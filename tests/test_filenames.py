import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class FilenameTests(unittest.TestCase):
    def test_names_in_both_hosts(self):
        for relative in ('native_host/host.py', 'native_host_full/host_runtime.py'):
            spec = importlib.util.spec_from_file_location('host_under_test', ROOT / relative)
            host = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(host)
            cases = {
                'movie.mkv': 'movie.mkv',
                'song.MP3': 'song.MP3',
                'track.flac': 'track.flac',
                'movie': 'movie.mkv',
                '': 'video.mkv',
                '...': 'video.mkv',
                'CON': '_CON.mkv',
                'nul.mp3': '_nul.mp3',
                'LPT9.flac': '_LPT9.flac',
                'CON.extra.mkv': '_CON.extra.mkv',
                'console.mkv': 'console.mkv',
                '../movie.mkv': 'movie.mkv',
                r'C:\videos\movie.mkv': 'movie.mkv',
                'bad:name?.mkv': 'bad_name_.mkv',
            }
            for source, expected in cases.items():
                with self.subTest(host=relative, source=source):
                    self.assertEqual(host.clean_name(source), expected)
            for suffix in ('.mkv', '.mp3', '.flac'):
                with self.subTest(host=relative, suffix=suffix):
                    name = host.clean_name('a' * 300 + suffix)
                    self.assertEqual(len(name), 180)
                    self.assertTrue(name.endswith(suffix))


if __name__ == '__main__':
    unittest.main()
