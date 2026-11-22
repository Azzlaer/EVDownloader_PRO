import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("youtube_provider", ROOT / "native_host" / "youtube_provider.py")
provider = importlib.util.module_from_spec(spec)
spec.loader.exec_module(provider)

class YouTubeProviderTests(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(provider.normalize_video_url("https://youtu.be/abcdefghijk"), "https://www.youtube.com/watch?v=abcdefghijk")
        self.assertEqual(provider.normalize_video_url("https://www.youtube.com/shorts/abcdefghijk"), "https://www.youtube.com/watch?v=abcdefghijk")
        self.assertEqual(provider.normalize_video_url("https://www.youtube.com/watch?v=abcdefghijk&list=PL123"), "https://www.youtube.com/watch?v=abcdefghijk")

    def test_reject_unsafe_urls(self):
        for url in ("http://youtu.be/abcdefghijk", "https://youtube.com.evil.test/watch?v=abcdefghijk",
                    "file:///etc/passwd", "https://www.youtube.com/playlist?list=abc",
                    "https://www.youtube.com/watch?v=invalid", "https://x:secret@youtube.com/watch?v=abcdefghijk"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                provider.normalize_video_url(url)

    def test_arguments(self):
        args = provider.download_args("https://youtu.be/abcdefghijk", "/tmp/video", "1080", "mkv")
        self.assertIn("--merge-output-format", args)
        self.assertIn("mkv", args)
        self.assertIn("bv*[height<=1080]+ba/b[height<=1080]", args)
        self.assertNotIn("shell", args)

    def test_audio_arguments(self):
        args = provider.download_args("https://youtu.be/abcdefghijk", "/tmp/audio", "best", "mp3")
        self.assertIn("--audio-format", args)
        self.assertIn("mp3", args)

    def test_quality_validation(self):
        with self.assertRaises(ValueError):
            provider.download_args("https://youtu.be/abcdefghijk", ".", "9999")
if __name__ == "__main__":
    unittest.main()
