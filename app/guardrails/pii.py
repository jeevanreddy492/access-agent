from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine

# Only these types are masked. Names are NOT masked on purpose:
# the agent needs "alice" to know who the request is for.
PII_TYPES = ["US_SSN", "CREDIT_CARD", "EMAIL_ADDRESS", "PHONE_NUMBER"]

_nlp = NlpEngineProvider(nlp_configuration={
    "nlp_engine_name": "spacy",
    "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
}).create_engine()

_analyzer = AnalyzerEngine(nlp_engine=_nlp, supported_languages=["en"])
_anonymizer = AnonymizerEngine()


def mask_pii(text):
    """Return (clean_text, list_of_pii_types_found)."""
    findings = _analyzer.analyze(text=text, entities=PII_TYPES, language="en")
    if not findings:
        return text, []
    clean = _anonymizer.anonymize(text=text, analyzer_results=findings).text
    found = sorted({f.entity_type for f in findings})
    return clean, found