"""Flask web application for viewing location history and managing iCloud auth."""

from __future__ import annotations

import hmac
import os
import time
from datetime import datetime, timedelta
from threading import RLock

from flask import Flask, jsonify, render_template, request

from .auth import AuthenticationError, ICloudAuth
from .database import LocationDatabase


def create_app(database: LocationDatabase, auth: ICloudAuth | None = None) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(
        __name__,
        template_folder="../../templates",
        static_folder="../../static",
    )

    web_auth_enabled = os.getenv("WEB_AUTH_ENABLED", "false").lower() in {"1", "true", "yes"}
    admin_password = os.getenv("WEB_ADMIN_PASSWORD", "")
    lifetime_days = max(1, int(os.getenv("AUTH_SESSION_LIFETIME_DAYS", "90")))
    auth_timeout = max(60, int(os.getenv("WEB_AUTH_FLOW_TIMEOUT_SECONDS", "600")))
    state = {"started_at": 0.0, "waiting_for_code": False}
    state_lock = RLock()

    def require_admin() -> tuple[dict, int] | None:
        if not web_auth_enabled:
            return {"error": "Web authentication is disabled"}, 404
        if not admin_password:
            return {"error": "WEB_ADMIN_PASSWORD is not configured"}, 503
        supplied = request.headers.get("X-Admin-Password", "")
        if not hmac.compare_digest(supplied, admin_password):
            return {"error": "Administrator authentication failed"}, 401
        return None

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Cache-Control", "no-store")
        return response

    @app.route("/")
    def index():
        """Main map view with an optional injected authentication widget."""
        html = render_template("index.html")
        if auth:
            assets = (
                '<link rel="stylesheet" href="/static/auth.css">\n'
                '<script defer src="/static/auth.js"></script>\n'
            )
            html = html.replace("</head>", f"{assets}</head>")
        return html

    @app.route("/api/auth/status")
    def api_auth_status():
        if not auth:
            return jsonify({"configured": False, "state": "unavailable"})
        status = auth.authentication_metadata(lifetime_days)
        status.update(
            web_auth_enabled=web_auth_enabled,
            admin_password_configured=bool(admin_password),
            username_masked=_mask_username(auth.username),
            lifetime_days=lifetime_days,
        )
        with state_lock:
            if state["waiting_for_code"] and time.monotonic() - state["started_at"] <= auth_timeout:
                status["flow_state"] = "waiting_for_code"
            else:
                state["waiting_for_code"] = False
                status["flow_state"] = "idle"
        return jsonify(status)

    @app.route("/api/auth/start", methods=["POST"])
    def api_auth_start():
        denied = require_admin()
        if denied:
            return jsonify(denied[0]), denied[1]
        if not auth:
            return jsonify({"error": "Apple ID is not configured"}), 503
        payload = request.get_json(silent=True) or {}
        password = payload.get("password") or auth.password
        if not password:
            return jsonify({"error": "Enter the Apple ID password or configure ICLOUD_PASSWORD"}), 400
        try:
            result = auth.begin_web_authentication(password)
            with state_lock:
                state["started_at"] = time.monotonic()
                state["waiting_for_code"] = bool(result["requires_2fa"])
            return jsonify(result)
        except AuthenticationError as exc:
            return jsonify({"error": str(exc)}), 400

    @app.route("/api/auth/verify", methods=["POST"])
    def api_auth_verify():
        denied = require_admin()
        if denied:
            return jsonify(denied[0]), denied[1]
        payload = request.get_json(silent=True) or {}
        code = str(payload.get("code", "")).strip()
        with state_lock:
            if not state["waiting_for_code"] or time.monotonic() - state["started_at"] > auth_timeout:
                state["waiting_for_code"] = False
                return jsonify({"error": "The authentication request expired. Start again."}), 409
        try:
            auth.complete_web_2fa(code)
            auth.get_devices()
            with state_lock:
                state["waiting_for_code"] = False
            return jsonify({"status": "authenticated"})
        except AuthenticationError as exc:
            return jsonify({"error": str(exc)}), 400

    @app.route("/api/devices")
    def api_devices():
        return jsonify(database.get_devices())

    @app.route("/api/locations")
    def api_locations():
        device_id = request.args.get("device_id")
        hours = request.args.get("hours", type=int)
        start = request.args.get("start")
        end = request.args.get("end")
        limit = request.args.get("limit", type=int, default=1000)
        start_time = datetime.now() - timedelta(hours=hours) if hours else None
        if start and not hours:
            start_time = datetime.fromisoformat(start)
        end_time = datetime.fromisoformat(end) if end else None
        return jsonify(database.get_locations(
            device_id=device_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        ))

    @app.route("/api/locations/latest")
    def api_latest_locations():
        latest = []
        for device in database.get_devices():
            location = database.get_latest_location(device["id"])
            if location:
                location["device_name"] = device["name"]
                location["device_display_name"] = device["device_display_name"]
                latest.append(location)
        return jsonify(latest)

    @app.route("/api/stats")
    def api_stats():
        devices = database.get_devices()
        return jsonify({
            "total_devices": len(devices),
            "total_locations": database.get_location_count(),
            "devices": [{
                "id": device["id"],
                "name": device["name"],
                "location_count": database.get_location_count(device["id"]),
                "last_seen": device["last_seen"],
                "latest_location": database.get_latest_location(device["id"]),
            } for device in devices],
        })

    return app


def _mask_username(username: str) -> str:
    if "@" not in username:
        return "***"
    local, domain = username.split("@", 1)
    visible = local[:1]
    return f"{visible}{'*' * max(3, len(local) - 1)}@{domain}"
