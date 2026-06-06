# Brain Score Concurrency

This is documented as a plugin capability now, even though Brain Score Concurrency will become an optional plugin later.

The LiveKit Vibes brain readiness score is read from `~/.openbase/brain_score.json` and exposed by the CLI at `/api/brain-readiness/`.

Concurrent agent threshold mapping:

| Brain readiness score | Concurrent agent threshold |
| --- | ---: |
| `< 25` | `1+` |
| `25` to `< 50` | `2+` |
| `50` to `< 75` | `4+` |
| `>= 75` | `7+` |

The backend computes the threshold from the exact `brs` value. The iOS app may display the score rounded to an integer, but it should use `parallel_voice_threshold` from `/api/brain-readiness/` for the concurrent-agent threshold whenever the score is available.

If no brain readiness score is available, iOS falls back to the locally stored muted-agent music threshold setting.
