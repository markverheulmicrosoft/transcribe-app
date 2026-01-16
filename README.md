# Transcribe App PoC

Een Proof of Concept applicatie voor het transcriberen van audio met automatische spreker-herkenning (diarization).

## Kenmerken

- **Spraak-naar-tekst transcriptie** met twee engines:
  - **Azure AI Speech (Fast Transcription API)** - aanbevolen voor Nederlands
  - Azure OpenAI gpt-4o-transcribe (beperkte taalondersteuning voor diarization)
- **Spreker-herkenning (diarization)** - onderscheidt automatisch verschillende sprekers
- **Concept Proces-Verbaal generatie** - automatische opmaak naar zakelijke weergave
- **Juridische entiteiten herkenning** - linkt naar wetten.overheid.nl
- **Export naar Word en PDF** - professioneel opgemaakte documenten
- **Volledig containerized** - eenvoudig te deployen
- **Veilig** - data blijft binnen Azure tenant via Private Endpoints

## Transcriptie Engines

### Azure AI Speech (Aanbevolen voor Nederlands)

De **Fast Transcription API** is de aanbevolen keuze voor Nederlandse spraakherkenning met sprekerherkenning:

| Feature | Specificatie |
|---------|--------------|
| **API** | Fast Transcription (v2025-10-15) |
| **Diarization** | Ingebouwde sprekerherkenning, **ondersteunt Nederlands** |
| **Max bestandsgrootte** | 300 MB (batch mode) |
| **Talen** | Nederlands (nl-NL), Engels, Duits, Frans |
| **Latency** | ~1-2 seconden per minuut audio |

### Azure OpenAI gpt-4o-transcribe (Alternatief)

> ⚠️ **Let op**: Dit model ondersteunt **geen Nederlandse diarization**. Sprekerherkenning werkt alleen voor Engels. Voor Nederlandse transcripties met sprekerherkenning, gebruik Azure AI Speech.

Alternatieve engine voor transcriptie zonder sprekerherkenning:

| Feature | Specificatie |
|---------|--------------|
| **Model** | gpt-4o-transcribe-diarize (2025-10-15) |
| **Diarization** | Alleen Engels ondersteund |
| **Max bestandsgrootte** | 25 MB |
| **Deployment** | Global Standard (East US 2, Sweden Central) |
| **Use case** | Engelse opnames, of Nederlandse transcriptie zonder sprekerherkenning |

## Ondersteunde Audio Formaten

| Type | Formaten |
|------|----------|
| **Native** | WAV, MP3, OGG, OPUS, FLAC, WMA, AAC, WEBM, AMR |
| **Container** | ASF (audio extractie via ffmpeg) |
| **Conversie nodig** | AVI, FLV, WMV, M4A, MP4 |

**Vereiste**: ffmpeg moet geïnstalleerd zijn voor niet-native formaten:
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg
```

## Installatie

### Vereisten

- Python 3.12+
- [UV](https://docs.astral.sh/uv/) - snelle Python package manager
- ffmpeg (voor audio conversie)
- Azure AI Speech resource (voor Speech engine)
- Azure OpenAI resource (optioneel, voor OpenAI engine)

### Stap 1: Azure Resources

#### Azure AI Speech

1. Maak een Azure AI Speech resource in Azure Portal
2. Kies regio: **West Europe** (aanbevolen voor latency)
3. Noteer de **Key** en **Region**

#### Azure OpenAI (optioneel)

1. Ga naar [Azure AI Foundry](https://ai.azure.com)
2. Deploy het **gpt-4o-transcribe-diarize** model
3. Beschikbare regio's: East US 2, Sweden Central

### Stap 2: Configuratie

```bash
# Clone en navigeer naar project
cd transcribe-app

# Kopieer environment template
cp .env.example .env
```

Vul de `.env` in:

```env
# Azure AI Speech (aanbevolen)
AZURE_SPEECH_KEY=your-speech-key
AZURE_SPEECH_REGION=westeurope

# Azure OpenAI (optioneel)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o-transcribe-diarize

# Standaard engine: "speech" of "openai"
TRANSCRIPTION_ENGINE=speech

# Applicatie settings
UPLOAD_DIR=./uploads
MAX_FILE_SIZE_MB=300
```

> Tip: gebruik `MAX_FILE_SIZE_MB=25` als je standaard Azure OpenAI gebruikt.

### Stap 3: Starten

```bash
# Installeer dependencies
make dev

# Start applicatie
make run
```

Open http://localhost:8000 in je browser.

## Gebruik

### Basis Workflow

1. **Upload** een audiobestand (max 25 MB voor OpenAI, 300 MB voor Speech)
2. **Selecteer** de taal (Nederlands, Engels, Duits, Frans)
3. **Kies** de transcriptie engine
4. **Start** de transcriptie
5. **Bekijk** het resultaat met spreker-labels

### Geavanceerde Features

#### Concept Proces-Verbaal

Genereer automatisch een zakelijke weergave van het verhandelde:
- Klik op de tab "Concept Proces-Verbaal"
- Het systeem groepeert uitspraken per spreker
- Output geschikt als basis voor officieel PV

#### Juridische Entiteiten

Automatische herkenning en linking van juridische termen:
- Algemene wet bestuursrecht (Awb) → [wetten.overheid.nl](https://wetten.overheid.nl/BWBR0005537)
- Wet open overheid (Woo) → [wetten.overheid.nl](https://wetten.overheid.nl/BWBR0045754)
- En andere veelvoorkomende wetten

### Export

- **Word** (.docx) - Professioneel opgemaakt document
- **PDF** - Print-ready formaat

## API Reference

| Method | Endpoint | Beschrijving |
|--------|----------|--------------|
| `GET` | `/` | Web interface |
| `GET` | `/api/health` | Health check |
| `GET` | `/api/config` | Applicatie configuratie |
| `POST` | `/api/transcribe` | Start transcriptie |
| `GET` | `/api/transcription/{job_id}` | Status/resultaat ophalen |
| `GET` | `/api/transcription/{job_id}/export/word` | Export naar Word |
| `GET` | `/api/transcription/{job_id}/export/pdf` | Export naar PDF |
| `DELETE` | `/api/transcription/{job_id}` | Verwijder transcriptie |

### Transcriptie Request

```bash
curl -X POST http://localhost:8000/api/transcribe \
  -F "file=@zitting.wav" \
  -F "language=nl" \
  -F "engine=speech"
```

### Response

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "message": "Transcription started (engine: speech)"
}
```

## Project Structuur

```
transcribe-app/
├── app/
│   ├── main.py                 # FastAPI applicatie
│   ├── config.py               # Configuratie settings
│   └── services/
│       ├── speech_service.py       # Azure OpenAI transcriptie
│       ├── azure_speech_service.py # Azure AI Speech transcriptie
│       ├── audio_converter.py      # ffmpeg audio conversie
│       └── export_service.py       # Word/PDF export
├── static/
│   └── index.html              # Frontend UI
├── tests/
│   ├── test_api.py             # API tests
│   └── test_audio_converter.py # Converter tests
├── pyproject.toml              # Project configuratie
├── Makefile                    # Development commands
  └── LICENSE
```

## Development

### Make Commands

| Command | Beschrijving |
|---------|--------------|
| `make dev` | Installeer dependencies met UV |
| `make run` | Start app met hot reload |
| `make test` | Run pytest tests |
| `make test-cov` | Tests met coverage |
| `make lint` | Run ruff linter |
| `make format` | Format code |
| `make typecheck` | Run mypy |
| `make clean` | Verwijder cache bestanden |

### Testing

```bash
# Run alle tests
make test

# Met coverage
make test-cov

# Specifieke test
uv run pytest tests/test_api.py -v
```

## Veiligheid en Compliance

### Richtlijnen

- **Data minimalisatie**: Audio wordt standaard verwijderd na verwerking.
- **Transport**: Gebruik TLS 1.2+ voor alle verbindingen.
- **Netwerk**: Configureer Private Endpoints/VNet indien vereist door beleid.
- **Compliance**: Beoordeel AVG/AI-verordening op basis van jouw deployment en data-classificatie.

## Roadmap

### Huidige Status (PoC)

- [x] Transcriptie met sprekerherkenning
- [x] Twee engines (Azure Speech, OpenAI)
- [x] Export naar Word/PDF
- [x] Concept Proces-Verbaal generatie
- [x] Juridische entiteiten herkenning

### Fase 2: Nice-to-haves

- [ ] Koppeling met e-dossier/zaaksysteem
- [ ] Ondersteuning voor vergaderingen
- [ ] Spreker-identificatie (naam toekennen)
- [ ] Chunking voor grote bestanden

### Fase 3: Toekomst

- [ ] Automatische PV generatie met GPT-4o
- [ ] Samenvatting en analyse
- [ ] MS Teams integratie
- [ ] Event-driven architectuur (Blob trigger → auto-transcriptie)

## Licentie

MIT License. Zie [LICENSE](LICENSE).

---

*Laatste update: Januari 2026*
