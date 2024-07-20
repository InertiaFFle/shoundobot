# shoundobot

using [pycord](https://github.com/Pycord-Development/pycord) and [pytubefix](https://github.com/JuanBindez/pytubefix)

it's a very simple discord [youtube](https://www.youtube.com/t/terms#c3e2907ca8) music bot ;)

## shoundobot commands

```txt
(prefix)(command)[(alias)]
<> - required
{} - optional
```

```txt
music box manager:

-add[-a] <video_url|playlist_url|search_query>
-remove[-r] <song_number>
-queue[-q]
-clear_queue[-cq]
-now_playing[-np]
-loop_queue[-l]
-shuffle_queue[-sh]

music player controller: 
-play[-p]
-disconnect[-dc]
-skip[-s] {song_number}

admin:
-restart_bot[-rr]
-stats[-ss]
```

## self hosting

you need ffmpeg in your machine

### build command

```bash
apt-get update && apt-get install -y ffmpeg && pip install -r requirements.txt
```

### start command

```bash
python bot.py
```