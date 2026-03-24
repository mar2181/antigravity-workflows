import sys
from youtube_transcript_api import YouTubeTranscriptApi

def get_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        text = " ".join([entry['text'] for entry in transcript])
        with open("transcript.txt", "w", encoding="utf-8") as f:
            f.write(text)
        print("Transcript saved to transcript.txt")
    except Exception as e:
        print(f"Error fetching transcript: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        get_transcript(sys.argv[1])
    else:
        print("Usage: python fetch_transcript.py <VIDEO_ID>")
