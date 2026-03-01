import os, base64, json
from flask import Flask, request, jsonify, render_template
import urllib.request

app = Flask(__name__)
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/check", methods=["POST"])
def check():
    try:
        data = request.json
        image_b64 = data.get("image_b64")
        image_type = data.get("image_type", "image/jpeg")
        ref_marks = data.get("ref_marks", [])

        if not image_b64 or not ref_marks:
            return jsonify({"error": "ข้อมูลไม่ครบ"}), 400

        ref_text = "\n".join([f"{i+1}. [{d['port']}] {d['mark']}" for i, d in enumerate(ref_marks)])

        prompt = f"""You are a QC system for shipping marks on cargo boxes.

REFERENCE Shipping Marks ({len(ref_marks)} items):
{ref_text}

TASK: Read ALL text from the image carefully, then compare with each reference above.

Respond ONLY in this exact JSON (no other text):
{{
  "extracted_text": "exact text from image",
  "matches": [
    {{
      "ref_index": 1,
      "ref_mark": "reference text",
      "port": "port name",
      "match_status": "PASS or FAIL",
      "differences": ["differences or empty if PASS"],
      "similarity_pct": 95
    }}
  ],
  "overall": "PASS or FAIL",
  "notes": "observations"
}}

One character difference = FAIL."""

        payload = json.dumps({
            "model": "claude-opus-4-6",
            "max_tokens": 1000,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": image_type, "data": image_b64}},
                    {"type": "text", "text": prompt}
                ]
            }]
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01"
            },
            method="POST"
        )

        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode("utf-8"))

        raw = "".join(c.get("text", "") for c in result.get("content", []))
        start = raw.find("{")
        end = raw.rfind("}") + 1
        parsed = json.loads(raw[start:end])
        return jsonify(parsed)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
