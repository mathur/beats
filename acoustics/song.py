from db import Song, Session, engine
from os import walk
from os.path import splitext, join
from mutagen.mp3 import EasyMP3
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis
from mutagen.mp4 import MP4
from sqlalchemy.sql.expression import or_

def remove_songs_in_dir(path):
    session = Session()
    session.query(Song).filter(Song.path.like(path + '%')).delete(synchronize_session='fetch')
    session.commit()

def add_songs_in_dir(path):
    remove_songs_in_dir(path)
    songs = []
    for root, _, files in walk(path):
        for f in files:
            ext = splitext(f)[1]
            filepath = join(root, f)
            if ext in {'.mp3', '.flac', '.ogg', '.m4a', '.mp4'}:
                try:
                    if ext == '.mp3':
                        song = EasyMP3(filepath)
                    elif ext == '.flac':
                        song = FLAC(filepath)
                    elif ext == '.ogg':
                        song = OggVorbis(filepath)
                    elif ext in {'.m4a', '.mp4'}:
                        song = MP4(filepath)
                except IOError, e:
                    print e
                    continue

                # Required tags
                try:
                    if ext in {'.m4a', '.mp4'}:
                        title = song.tags['\xa9nam'][0]
                        artist = song.tags['\xa9ART'][0]
                        album = song.tags['\xa9alb'][0]
                    else:
                        title = song.tags['title'][0]
                        artist = song.tags['artist'][0]
                        album = song.tags['album'][0]
                except Exception:
                    print 'Skipped: ' + filepath
                    continue

                song_obj = {'title': title,
                    'artist': artist,
                    'album': album,
                    'length': song.info.length,
                    'path': filepath}

                try:
                    if ext in {'.m4a', '.mp4'}:
                        song_obj['tracknumber'] = song.tags['trkn'][0][0]
                    else:
                        song_obj['tracknumber'] = int(song.tags['tracknumber'][0])
                except Exception:
                    song_obj['tracknumber'] = None

                songs.append(song_obj)
    if not songs:
        return 0

    table = Song.__table__
    conn = engine.connect()
    conn.execute(table.insert(), songs)
    conn.close()

    return len(songs)

def search_songs(query, limit=20):
    songs = []
    if query:
        session = Session()
        res = session.query(Song).filter(or_(
            Song.title.like('%' + query + '%'),
            Song.artist.like('%' + query + '%'),
            Song.album.like('%' + query + '%'))) \
                    .limit(limit).all()
        session.commit()
        songs = [song.dictify() for song in res]
    return {'query': query, 'limit': limit, 'results': songs}
