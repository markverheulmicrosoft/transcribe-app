# Transcriptie PoC - Raad van State

Een Proof of Concept applicatie voor het transcriberen van zittingen met automatische spreker-herkenning (diarization).

## Kenmerken

- 🎙️ **Spraak-naar-tekst transcriptie** met Azure OpenAI gpt-4o-transcribe-diarize
- 👥 **Spreker-herkenning (diarization)** - onderscheidt automatisch verschillende sprekers
- 📄 **Export naar Word en PDF** - professioneel opgemaakte documenten
- �� **Volledig containerized** - eenvoudig te deployen
- 🔒 **Veilig** - data blijft binnen Azure tenant (Azure Foundry)

## Technische Architectuur

### Data Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           RVDS Azure Tenant                                   │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐        │
│  │   Web Browser   │────▶│  Transcribe App │────▶│  Azure OpenAI   │        │
│  │   (Upload UI)   │     │  (Container)    │     │  Service        │        │
│  └─────────────────┘     └─────────────────┘     └─────────────────┘        │
│         │                        │                       │                   │
│         │                        │                       │                   │
│         ▼                        ▼                       ▼                   │
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐        │
│  │  Audio Upload   │     │  Transcriptie   │     │   AI Model      │        │
│  │  (lokaal/temp)  │     │  Resultaat      │     │   gpt-4o-       │        │
│  └─────────────────┘     │  (JSON)         │     │   transcribe-   │        │
│                          └─────────────────┘     │   diarize       │        │
│                                  │               └─────────────────┘        │
│                                  ▼                                           │
│                          ┌─────────────────┐                                 │
│                          │  Export         │                                 │
│                          │  (Word/PDF)     │                                 │
│                          └─────────────────┘                                 │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Technische Componenten

| Component | Technologie | Beschrijving |
|-----------|-------------|--------------|
| **Frontend** | HTML/CSS/JavaScript | Eenvoudige upload interface |
| **Backend** | FastAPI (Python 3.12) | REST API voor transcriptie |
| **Transcriptie** | Azure OpenAI | gpt-4o-transcribe-diarize model |
| **AI Model** | gpt-4o-transcribe-diarize (2025-10-15) | Spraakherkenning met ingebouwde diarization |
| **Export** | python-docx, ReportLab | Word en PDF generatie |
| **Container** | Docker | Deployment |

## gpt-4o-transcribe-diarize Model

### Waarom gpt-4o-transcribe-diarize?

Dit model is de ideale keuze voor deze PoC omdat het:

| Feature | gpt-4o-transcribe-diarize | Azure OpenAI Whisper | Azure Speech Service |
|---------|---------------------------|---------------------|---------------------|
| Spreker-herkenning (diarization) | ✅ **Ingebouwd** | ❌ Niet beschikbaar | ✅ Ondersteund |
| AI Model | GPT-4o gebaseerd | Whisper | Azure Base Model |
| Max. bestandsgrootte | 25 MB | 25 MB | 1 GB (batch) |
| Nederlands (nl-NL) | ✅ | ✅ | ✅ |
| Data in Azure Tenant | ✅ Via Foundry | ✅ | ✅ |
| Eenvoudige integratie | ✅ OpenAI SDK | ✅ OpenAI SDK | ⚠️ Speech SDK |

**Conclusie:** `gpt-4o-transcribe-diarize` combineert de kracht van GPT-4o met ingebouwde speaker diarization, perfect voor zittingen.

### Model Specificaties

- **Model naam**: `gpt-4o-transcribe-diarize`
- **Versie**: 2025-10-15
- **Max bestandsgrootte**: 25 MB
- **Ondersteunde formaten**: MP3, MP4, MPEG, MPGA, M4A, WAV, WEBM
- **Output**: Verbose JSON met segments en speaker labels

## Installatie

### Vereisten

- Python 3.12+ (voor lokale development)
- [UV](https://docs.astral.sh/uv/) - snelle Python package manager (aanbevolen)
- Docker en Docker Compose (voor container deployment)
- Azure OpenAI Service met gpt-4o-transcribe-diarize deployment (via Azure Foundry)

### Stap 1: Clone en configureer

```bash
# Clone repository
cd transcribe-app

# Kopieer environment template
cp .env.example .env

# Bewerk .env met je Azure credentials
nano .env
```

### Stap 2: Vul de .env in

```env
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o-transcribe-diarize
```

### Stap 3: Lokale Development (met UV)

```bash
# Installeer UV (indien nog niet geïnstalleerd)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Installeer dependencies (incl. dev tools)
make dev
# of: uv sync

# Start de applicatie met hot reload
make run
# of: uv run uvicorn app.main:app --reload

# Run tests
make test
# of: uv run pytest -v

# Lint en format code
make lint
make format
```

### Stap 3b: Docker Deployment

```bash
# Build en start met Docker Compose
make docker-run
# of: docker-compose up -d

# Stop containers
make docker-stop
# of: docker-compose down
```

### Stap 4: Open de applicatie

Open http://localhost:8000 in je browser.

## Gebruik

1. **Upload** een audiobestand (WAV, MP3, M4A, OGG, of WEBM) - max 25 MB
2. **Selecteer** de taal van de opname
3. **Start** de transcriptie
4. **Bekijk** het resultaat met spreker-labels (automatisch gedetecteerd)
5. **Exporteer** naar Word of PDF

## Development

### Project Structuur

```
transcribe-app/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI applicatie
│   ├── config.py            # Configuratie settings
│   ├── services/
│   │   ├── speech_service.py    # Azure OpenAI transcriptie
│   │   └── export_service.py    # Word/PDF export
│   └── static/
│       └── index.html       # Frontend UI
├── tests/
│   └── test_api.py          # API tests
├── pyproject.toml           # Project configuratie (UV/pip)
├── Makefile                 # Development commands
├── Dockerfile
├── docker-compose.yml
└── README.md
```

### Beschikbare Make Commands

| Command | Beschrijving |
|---------|--------------|
| `make dev` | Installeer alle dependencies met UV |
| `make run` | Start app lokaal met hot reload |
| `make test` | Run pytest tests |
| `make test-cov` | Tests met coverage report |
| `make lint` | Run ruff linter |
| `make format` | Format code met ruff |
| `make typecheck` | Run mypy type checker |
| `make docker-build` | Build Docker image |
| `make docker-run` | Start met Docker Compose |
| `make clean` | Verwijder cache bestanden |

### Testing

```bash
# Run alle tests
make test

# Run tests met coverage
make test-cov

# Run specifieke test
uv run pytest tests/test_api.py::TestHealthEndpoints -v
```

## Veiligheid en Compliance

### Data Flow en Verwerking

```
Audio Upload → Container (lokaal) → Azure OpenAI → Resultaat → Export
     │              │                    │              │
     ▼              ▼                    ▼              ▼
   TLS 1.2     Tijdelijke          Azure Tenant     Verwijdering
              opslag               (via Foundry)    na verwerking
```

### Beveiligingsmaatregelen

| Aspect | Maatregel |
|--------|-----------|
| **Transport** | TLS 1.2 voor alle verbindingen |
| **Data at rest** | Audio wordt na transcriptie verwijderd |
| **Azure Tenant** | Data blijft binnen eigen tenant via Azure Foundry |
| **Authenticatie** | API Key of Managed Identity (aanbevolen voor productie) |
| **Netwerk** | Kan binnen VNet gedeployed worden |

### DPIA Overwegingen

| Vraag | Antwoord |
|-------|----------|
| Waar wordt data verwerkt? | Binnen Azure tenant (via Azure Foundry) |
| Blijft data in Azure tenant? | Ja, Azure OpenAI in eigen tenant |
| Wordt data opgeslagen door Microsoft? | Nee, geen data opslag voor training |
| Welke AI modellen worden gebruikt? | gpt-4o-transcribe-diarize (Microsoft/OpenAI) |
| Is er sprake van training op data? | Nee, geen model training op klantdata |

### AI-Verordening Compliance

- **Transparantie**: Duidelijk dat AI wordt gebruikt voor transcriptie
- **Menselijke controle**: Transcript kan worden gereviewd en gecorrigeerd
- **Data minimalisatie**: Audio wordt verwijderd na verwerking
- **Geen profiling**: Geen besluitvorming gebaseerd op AI-output
- **Data soevereiniteit**: Verwerking binnen eigen Azure tenant

## API Endpoints

| Method | Endpoint | Beschrijving |
|--------|----------|--------------|
| GET | `/` | Web interface |
| GET | `/api/health` | Health check |
| GET | `/api/config` | Applicatie configuratie |
| POST | `/api/transcribe` | Start transcriptie |
| GET | `/api/transcription/{job_id}` | Status/resultaat ophalen |
| GET | `/api/transcription/{job_id}/export/word` | Export naar Word |
| GET | `/api/transcription/{job_id}/export/pdf` | Export naar PDF |
| DELETE | `/api/transcription/{job_id}` | Verwijder transcriptie |

## Toekomstige Uitbreidingen

### Stap 2: Nice-to-haves
- [ ] Koppeling met e-dossier/zaaksysteem
- [ ] Ondersteuning voor vergaderingen
- [ ] Spreker-identificatie (naam toekennen aan spreker)
- [ ] Chunking voor bestanden > 25 MB

### Stap 3: Toekomst
- [ ] Automatische generatie van Proces Verbaal
- [ ] Samenvatting met Azure OpenAI GPT-4o
- [ ] Integratie met MS Teams voor live transcriptie

## Technisch Verwerkingsproces

```
1. UPLOAD
   └─ Gebruiker uploadt audio via browser
   └─ Bestand wordt tijdelijk opgeslagen in container
   └─ Validatie van formaat en grootte (max 25 MB)

2. TRANSCRIPTIE
   └─ Verbinding naar Azure OpenAI Service (TLS 1.2)
   └─ gpt-4o-transcribe-diarize API aanroep
   └─ Audio wordt verzonden met verbose_json response format
   └─ Model: gpt-4o-transcribe-diarize met ingebouwde diarization
   └─ Data verwerking: binnen eigen Azure tenant

3. RESULTAAT
   └─ JSON response met segmenten en spreker-IDs
   └─ Opslag in geheugen (geen persistente database in PoC)
   └─ Origineel audiobestand wordt verwijderd

4. EXPORT
   └─ Generatie van Word/PDF lokaal in container
   └─ Download naar gebruiker

5. CLEANUP
   └─ Automatische verwijdering na sessie/timeout
```

## Licentie

Intern gebruik - Raad van State
