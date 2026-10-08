🐾 CatColonyWatch
Observe first. Record second. Let open AI structure the notes.
CatColonyWatch is an open-source field-observation tool for volunteers and organisations that monitor community-cat colonies.
The central idea is simple:
The AI is not watching the cats. The human is.

The app is designed to keep screen time short. A volunteer goes to the colony, observes what is happening, records factual notes, and then uses a local open-weight AI model to structure those observations into a clearer record.
🌿 What CatColonyWatch is for
Community-cat monitoring happens in the real world: at feeding points, streets, gardens, shelters, courtyards, and other shared spaces.
CatColonyWatch supports a simple workflow:
1. Go to the colony or feeding point.
2. Observe for a few minutes.
3. Record the cats actually seen.
4. Add factual notes about individual cats, the environment, and other animals.
5. Let local open-weight AI structure the observations.
6. Review the AI output before saving or exporting it.
The project does not use AI to replace observation.
It uses AI after observation to help create more consistent and reusable records.
🐈 Main features
Cat database
Known cats can be registered once and selected again during future visits.
A cat record can include:
- name or field name
- colony / feeding point
- sex
- estimated age
- sterilisation status
- ear-tip / visible sterilisation mark
- optional existing identifier
- coat and identifying features
- health notes
- general notes
- next step or decision
- follow-up status
- optional target date
Internal database IDs are kept hidden from volunteers.
Field visits
Each observation visit can record:
- date
- observation start time
- observation end time
- automatically calculated duration
- observer
- colony / feeding point
- weather
- known cats observed
- individual notes for known cats
- unidentified cats
- total cats observed
- food and water availability
- feeding-point / shelter condition
- biodiversity / other animals observed
- general field notes
Future observation dates are not allowed.
When recording a visit on the current day, the observation end time cannot be in the future.
Unidentified cats
A volunteer can record a cat that is not yet in the database without creating a permanent profile immediately.
For each unidentified cat, the visit can store:
- temporary label
- sex, if known
- estimated age
- coat / identifying features
- factual observation notes
Total cats observed
The total count includes:
- known cats selected in the visit
- unidentified cats recorded individually
- additional cats seen but not described individually
This allows the visit to preserve the overall number of cats observed even when not every individual can be identified.
Visit history
Saved visits can be reviewed later together with the cats associated with that visit.
Data export
Reviewed visits can be exported as:
- JSON
- CSV
Portable formats make it easier to reuse the data in other systems or future integrations.
🤖 Open-weight AI: Gemma + Ollama
CatColonyWatch uses Gemma 3, an open-weight model, running locally through Ollama.
Default model:
gemma3:4b
Ollama provides the model through a local API:
http://localhost:11434
The Streamlit application sends the observation data to the local Ollama server and receives structured JSON back from Gemma.
No paid inference API is required.
After the model has been downloaded, inference can run locally on the user's computer.
🧠 What the AI does
The AI has one deliberately narrow role:
Structure field observations into a clearer record.

It is asked to:
- preserve factual observations
- preserve uncertainty
- organise notes about individual cats
- organise colony and environmental observations
- organise biodiversity observations
- distinguish observed facts from interpretation
- identify objective items that may deserve later follow-up
The full observation context can be sent to the model, including:
- visit date and time
- colony
- observer
- weather
- known cats and their visit-specific notes
- unidentified cats and their observed features
- food and water
- feeding-point condition
- biodiversity observations
- free-text notes
⚠️ What the AI does not do
CatColonyWatch does not use AI to:
- diagnose animals
- assess medical urgency
- recommend treatment
- infer disease
- infer emotions
- infer intentions
- invent missing information
- replace veterinary judgement
- replace experienced colony-management teams
All AI-generated output requires human review before it is treated as part of the observation record.
🔒 Why local AI matters
Community-cat monitoring may involve sensitive information such as:
- animal locations
- colony routines
- volunteer activity
- feeding points
- health observations
- association or municipal workflows
Running Gemma locally through Ollama means field notes can be processed without sending them to a third-party AI API.
This gives users and organisations more control over:
- privacy
- infrastructure
- model choice
- costs
- evaluation
- customisation
- future integrations
The AI component is also replaceable. CatColonyWatch is not tied to a closed model provider.
A future version could use another open-weight model, a smaller local model, or an organisation-specific model without redesigning the whole application.
🔓 Why open innovation matters
Open innovation is central to CatColonyWatch.
The project combines open-source software with an open-weight model so that others can inspect, adapt, improve, and reuse the system.
This matters because community-cat work is carried out by very different groups:
- individual volunteers
- animal-welfare associations
- shelters
- municipalities
- researchers
- community projects
Their workflows and constraints are not identical.
An open project allows them to adapt:
- the observation schema
- the database
- the AI prompt
- the model
- the interface
- the export format
- future integrations
Open components also reduce vendor lock-in and make experimentation easier.
🧩 Complementing existing colony-management tools
CatColonyWatch is not intended to replace comprehensive colony-management platforms.
Tools such as Meow Metrics address broader colony-management needs, including long-term colony administration, identification, veterinary information, and CER/TNR workflows.
CatColonyWatch focuses on a narrower question:
How can volunteers collect better structured observations while physically monitoring a colony?

Its role is best understood as an open-source field-observation layer.
The project concentrates on:
- short field visits
- reusable cat records
- unidentified-cat observations
- factual note-taking
- biodiversity context
- local open-weight AI
- exportable JSON/CSV data
Because the project is open source and uses portable data formats, it could potentially be adapted to complement broader colony-management workflows, research projects, municipal systems, volunteer organisations, or existing platforms such as Meow Metrics.
🌍 Biodiversity context
Community-cat colonies exist within wider urban and peri-urban ecosystems.
For that reason, CatColonyWatch also allows volunteers to record observations about:
- birds
- small mammals
- reptiles
- other animals
- changes around feeding points
- environmental conditions
The app does not automatically draw ecological conclusions from these observations.
Its goal is to preserve factual field data that may later support better understanding of the wider environment around a colony.
🗄️ Local database
CatColonyWatch uses SQLite.
The local database file is:
catcolonywatch.db
It stores:
- registered cats
- field visits
- known cats observed during each visit
- visit-specific notes
- unidentified cats observed during visits
- structured AI output
SQLite is well suited to the current prototype because it is lightweight, local, easy to inspect, and easy to back up.
Deployment note
SQLite works well for local use and demonstrations.
On platforms with ephemeral filesystems, persistence may not be guaranteed across restarts or redeployments.
A production multi-user version should use a persistent database such as PostgreSQL.
🛠️ Tech stack
- Python
- Streamlit
- SQLite
- Ollama
- Gemma 3
- Requests
- Pandas
🏗️ Architecture
Human field observation
        ↓
Streamlit interface
        ↓
Structured visit data
        ↓
Local Ollama server
        ↓
Gemma 3 open-weight model
        ↓
Structured JSON
        ↓
Human review
        ↓
SQLite + JSON/CSV export
The human observation comes first.
The AI only processes information that the volunteer has already recorded.
🚀 Run locally
1. Clone the repository
git clone https://github.com/Maribele/CatColonyWatch.git
cd CatColonyWatch
2. Create a virtual environment
python3 -m venv .venv
Activate it on macOS/Linux:
source .venv/bin/activate
3. Install Python dependencies
python -m pip install -r requirements.txt
4. Install Ollama
On macOS:
curl -fsSL https://ollama.com/install.sh | sh
You can also install Ollama using the official installer for your operating system.
5. Start Ollama
In one terminal:
ollama serve
Leave this terminal running.
6. Download Gemma
In another terminal:
ollama pull gemma3:4b
The model only needs to be downloaded once.
You can verify the installed models with:
ollama list
7. Launch CatColonyWatch
With the Python virtual environment activated:
python -m streamlit run app.py
Then open the local Streamlit URL shown in the terminal.
When the local AI connection is ready, the app displays:
Local AI ready · Ollama · Model: gemma3:4b
☁️ Streamlit and deployment
CatColonyWatch uses Streamlit as its interface.
The complete application currently works best locally:
Streamlit UI + local Ollama + local Gemma
This architecture is intentional because it allows the AI processing to remain on the user's machine.
A standard Streamlit Community Cloud deployment cannot directly access an Ollama server running on a visitor's local computer.
A hosted version could later connect to a self-hosted open-weight model endpoint while keeping the same general architecture.
🧪 Example workflow
A volunteer observes:
Mora ate at the feeding point for about four minutes.
Leo walked while putting less weight on the left hind leg.
One unidentified orange cat stayed close to the bushes.
Two magpies were feeding about five metres away.
Gemma can structure the notes into categories such as:
Observed facts
- Mora ate at the feeding point for approximately four minutes.
- Leo placed less weight on the left hind leg while walking.
- An unidentified orange cat remained near the bushes.

Biodiversity
- Two magpies were observed feeding approximately five metres away.

Follow-up flags
- Change in Leo's weight-bearing during walking.
The model does not diagnose Leo.
It only structures the observation made by the human.
🔐 Privacy and data
By default:
- cat and visit data are stored locally in SQLite
- AI inference runs locally through Ollama
- no paid external inference API is required
Users should still avoid publishing sensitive colony locations or personal volunteer information unless they have a legitimate reason and appropriate permission to do so.
The local database should not be committed to a public repository if it contains real colony data.
📁 Repository notes
Files such as the following should normally stay out of Git:
.venv/
catcolonywatch.db
.streamlit/secrets.toml
__pycache__/
A .gitignore file should be used to prevent accidental publication of local or sensitive data.
🧭 Future development
Possible next steps include:
- shared multi-user colony databases
- PostgreSQL persistence
- photo attachments
- longitudinal timelines for individual cats
- absence / reappearance tracking
- configurable observation schemas
- association or municipality dashboards
- import/export connectors for existing colony-management systems
- offline-first field workflows
- local model comparison
- multilingual interfaces
- aggregated biodiversity observations
Any future AI feature should preserve the same principle:
AI assists observation. It does not replace human judgement.

🎥 Demo
A demonstration can show the complete workflow:
1. register a known cat
2. start a field visit
3. select known cats observed
4. add an unidentified cat
5. record environmental and biodiversity notes
6. structure the visit with local Gemma
7. review the AI-generated record
8. save the visit
9. inspect visit history
10. export the data

📄 License
This project is licensed under the MIT License.
You are free to use, modify, distribute, and integrate the code in other projects, including community-cat management tools, research projects, volunteer initiatives, and municipal or organisational systems, provided that the original copyright and license notice are preserved.
See the LICENSE file for details.

❤️ Core principle
Observe first. Record second. Let open AI structure the notes.

The screen should support the fieldwork — not replace it.