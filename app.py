from flask import Flask, render_template, request
from bs4 import BeautifulSoup
import requests
import ollama
import markdown
from flask_cors import CORS
from requests.exceptions import RequestException

MODEL = "llama3.2"   

app = Flask(__name__)
CORS(app)  

class Website:
    def __init__(self, url):
        self.url = url
        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            resp = requests.get(url, timeout=10, headers=headers)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content, 'html.parser')
            self.title = soup.title.string if soup.title else "No title"
            for tag in soup.body(["script", "style", "img", "input"]):
                tag.decompose()
            self.text = soup.body.get_text(separator="\n", strip=True)
        except Exception as e:
            summary = f"⚠️ Error during summarization: {e}"
            print(e)


system_prompt = (
    "You are an assistant that analyzes the contents of a website and provides "
    "a short summary, ignoring navigation text. Respond in markdown."
)

def user_prompt_for(site: Website):
    snippet = site.text[:1500]  # keep under token limits
    return (
        f"You are looking at a website titled “{site.title}”.\n\n"
        f"The contents of this website are as follows:\n\n{snippet}\n\n"
        "Please provide a concise summary in markdown."
    )

def summarize(url: str) -> str:
    site = Website(url)
    if site.title == "Error":
        return site.text  # Show the real error message

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt_for(site)}
    ]
    resp = ollama.chat(model=MODEL, messages=messages)
    return resp["message"]["content"]


# ————— Flask Routes —————
@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")

@app.route("/summarize", methods=["POST"])
def summarize_route():
    url = request.form.get("url", "")
    if not url:
        return render_template("index.html", summary="⚠️ Please provide a URL.", url=url)
    if not url.startswith(("http://", "https://")):
        return render_template("index.html", summary="⚠️ Invalid URL format.", url=url)
    try:
        summary = summarize(url)
        summary_html = markdown.markdown(summary)
    except Exception as e:
        summary_html = f"⚠️ Error during summarization: {e}"
        print(e)
    return render_template("index.html", summary=summary_html, url=url)

if __name__ == "__main__":
    # Set debug=True for development; set to False in production
    app.run(debug=True)
