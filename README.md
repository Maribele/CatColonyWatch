🐾 CatColonyWatch
Observe first. Record second. Let open AI structure the notes.
CatColonyWatch is an open-source field-observation tool for volunteers and organisations that monitor community-cat colonies.
The AI is not watching the cats. The human is.

The app is designed to keep screen time short: volunteers observe cats and their environment first, record factual notes second, and then use a local open-weight AI model to structure those observations into a clearer record.
🌿 How it works
1. Go to the colony or feeding point.
2. Observe for a few minutes.
3. Record the cats actually seen.
4. Add factual notes about individual cats, the environment, and other animals.
5. Let local open-weight AI structure the observations.
6. Review the AI output before saving or exporting it.
AI supports the fieldwork. It does not replace observation.
🐈 Main features
CatColonyWatch includes:
- a reusable database for known cats
- field visits with date, time, observer, weather and duration
- individual notes for known cats
- temporary records for unidentified cats
- total cats observed, including cats not identified individually
- food, water and feeding-point observations
- biodiversity and environmental notes
- visit history
- JSON and CSV export
- local SQLite storage
Internal database IDs are hidden from volunteers.
🤖 Open-weight AI: Gemma + Ollama
CatColonyWatch uses Gemma 3 running locally through Ollama.
Default model:
gemma3:4b
Ollama exposes the model locally at:
http://localhost:11434
The Streamlit app sends the recorded observation to the local Ollama server and receives structured JSON back from Gemma.
No paid inference API is required.
After the model has been downloaded, inference can run locally on the user's computer.
🧠 What the AI does
The AI has one deliberately narrow role:
Structure field observations into a clearer record.

It is instructed to:
- preserve factual observations
- preserve uncertainty
- organise information about individual cats
- organise environmental and biodiversity observations
- separate observed facts from interpretation
- flag objective items that may deserve later follow-up
It is explicitly instructed not to:
- diagnose
- assess medical urgency
- recommend treatment
- infer disease
- infer emotions or intentions
- invent missing information
- replace veterinary judgement
- replace experienced colony-management teams
All AI-generated output requires human review.
🔒 Why local AI matters
Community-cat monitoring can involve sensitive information such as animal locations, feeding points, volunteer activity and health observations.
Running Gemma locally through Ollama allows field notes to be processed without sending them to a third-party AI API.
This gives users and organisations more control over:
- privacy
- model choice
- infrastructure
- costs
- evaluation
- future customisation
The AI component is also replaceable, so CatColonyWatch is not tied to a closed provider.
🔓 Why open innovation matters
CatColonyWatch combines open-source software with an open-weight model so others can inspect, adapt, improve and reuse the project.
Different volunteers, associations, shelters, municipalities and researchers have different workflows. An open project makes it possible to adapt:
- the observation schema
- the database
- the AI prompt
- the model
- the interface
- export formats
- future integrations
🧩 Complementing existing colony-management tools
CatColonyWatch is not intended to replace comprehensive colony-management platforms.
Tools such as Meow Metrics address broader colony-management needs, including long-term colony administration, identification, veterinary information and CER/TNR workflows.
CatColonyWatch focuses on a narrower question:
How can volunteers collect better structured observations while physically monitoring a colony?

It is best understood as an open-source field-observation layer, with local AI and portable JSON/CSV data that could potentially complement broader colony-management, research or municipal workflows.
🌍 Biodiversity context
Community-cat colonies exist within wider urban and peri-urban ecosystems.
CatColonyWatch therefore also allows volunteers to record factual observations about:
- birds
- small mammals
- reptiles
- other animals
- feeding-point surroundings
- environmental changes
The app does not automatically draw ecological conclusions from isolated observations.
🗄️ Local database
CatColonyWatch uses SQLite.
The local database file is:
catcolonywatch.db
It stores cats, visits, visit-specific observations, unidentified cats and structured AI output.
The database is intentionally excluded from Git so real colony data is not published accidentally.
For a future multi-user production version, persistent storage such as PostgreSQL would be more appropriate.
🛠️ Tech stack
- Python
- Streamlit
- SQLite
- Ollama
- Gemma 3
- Requests
- Pandas
🚀 Run locally
Clone the repository:
git clone https://github.com/Maribele/CatColonyWatch.git
cd CatColonyWatch
Create and activate a virtual environment:
python3 -m venv .venv
source .venv/bin/activate
Install the dependencies:
python -m pip install -r requirements.txt
Install Ollama, then start it:
ollama serve
In another terminal, download Gemma:
ollama pull gemma3:4b
Launch the app:
python -m streamlit run app.py
When everything is ready, CatColonyWatch displays:
Local AI ready · Ollama · Model: gemma3:4b
☁️ Streamlit and deployment
CatColonyWatch uses Streamlit as its interface.
The complete AI workflow currently works best locally:
Streamlit UI + local Ollama + local Gemma
A standard Streamlit Community Cloud deployment cannot directly access an Ollama server running on a visitor's computer.
A future hosted version could connect to a self-hosted open-weight model endpoint while keeping the same general architecture.
🧭 Future development
Possible next steps include:
- shared multi-user colony databases
- PostgreSQL persistence
- photo attachments
- longitudinal timelines for individual cats
- absence / reappearance tracking
- configurable observation schemas
- association or municipality dashboards
- connectors for existing colony-management systems
- offline-first field workflows
- multilingual interfaces
- aggregated biodiversity observations
Any future AI feature should preserve the same principle:
AI assists observation. It does not replace human judgement.

📄 License
This project is licensed under the MIT License.
You are free to use, modify, distribute and integrate the code in other projects, provided that the original copyright and license notice are preserved.
See the LICENSE file for details.
❤️ Core principle
Observe first. Record second. Let open AI structure the notes.

The screen should support the fieldwork — not replace it.