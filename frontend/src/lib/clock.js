// One playback clock for the whole UI. Lives outside React so a 60fps tick never
// triggers a render. The backend is authoritative: we interpolate between its
// `playback` messages at exactly 1x speed and only correct real drift.

const now = () => performance.now() / 1000;

class Clock {
  constructor() {
    this.anchorPos = 0;
    this.anchorAt = now();
    this.playing = false;
    this.songId = null;
  }

  position() {
    return this.playing ? this.anchorPos + (now() - this.anchorAt) : this.anchorPos;
  }

  // msg: {song_id, position_sec, playing}
  update(msg) {
    const local = this.position();
    const drift = msg.position_sec - local;
    const newSong = msg.song_id !== this.songId;
    this.songId = msg.song_id;

    if (newSong || msg.playing !== this.playing || !msg.playing || Math.abs(drift) > 0.25) {
      this.anchorPos = msg.position_sec;          // hard set: seek / pause / new song
    } else if (Math.abs(drift) > 0.06) {
      this.anchorPos = local + drift * 0.5;       // gentle pull toward the server
    } else {
      return;                                      // within tolerance: leave the clock alone
    }
    this.anchorAt = now();
    this.playing = msg.playing;
  }
}

export const clock = new Clock();
