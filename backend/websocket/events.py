"""
WebSocket event handlers for Flask-SocketIO.
Manages real-time communication between backend and clients.

v2: Added ping/pong latency measurement and position_ms in status events.
"""

import time


def register_events(socketio, detector, cache, sync_engine=None):
    """
    Register all WebSocket event handlers.

    Args:
        socketio: Flask-SocketIO instance.
        detector: SongDetector instance.
        cache: LyricsCache instance.
        sync_engine: SyncEngine instance (for re-emitting lyrics state on reconnect).
    """

    @socketio.on('connect')
    def handle_connect():
        print('[WS] Client connected')
        # Don't send state here — the frontend immediately sends 'request_current'
        # after connecting, which handles the full state re-emit.

    @socketio.on('disconnect')
    def handle_disconnect():
        print('[WS] Client disconnected')

    @socketio.on('request_current')
    def handle_request_current():
        """Client requests current song state — includes lyrics + highlight."""
        current = detector.get_current_song()
        if current:
            socketio.emit('song_detected', {
                'title': current.get('title', ''),
                'artist': current.get('artist', ''),
                'album': current.get('album', ''),
                'source': current.get('source', 'unknown'),
                'position_ms': detector.get_playback_position(),
                'server_time': time.time(),
            })
            # Re-emit full lyrics state so the client gets the current line
            if sync_engine:
                sync_engine.emit_current_state()

    @socketio.on('request_position')
    def handle_request_position():
        """Client requests current playback position."""
        pos = sync_engine.get_position_ms() if sync_engine else detector.get_playback_position()
        socketio.emit('position_update', {
            'position_ms': pos,
            'server_time': time.time(),
        })

    @socketio.on('ping_sync')
    def handle_ping_sync(data):
        """
        Client ping for round-trip latency measurement.
        Client sends {client_time}, server responds with {client_time, server_time}.
        Client computes RTT = now - client_time, one-way latency ≈ RTT/2.
        """
        socketio.emit('pong_sync', {
            'client_time': data.get('client_time', 0),
            'server_time': time.time(),
        })
