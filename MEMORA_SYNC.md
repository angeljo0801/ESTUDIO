# Memora ↔ ChatGPT (v1.52)

Create a separate **private** GitHub repository, suggested name `angeljo0801/Memora-Sync`, initialized with a README. Grant the ChatGPT GitHub connector access to it. Create a fine-grained PAT restricted to that one repository, Contents read/write, and paste it only in the phone's Memora sync screen. The token is stored using flutter_secure_storage. The app refuses public repositories and does not follow redirects. Do not put user study content into ESTUDIO.

Open Biblioteca → sync icon → Guardar y verificar conexión. Operations are explicit:
- Download `memora-guides.json` from the private repository's default branch.
- Send requests to `memora-requests.json`, with schema 1 and requests array.
- Share study results of remotely synchronized guides only in `memora-progress.json`. No local guides, files or token are included. GitHub file SHA protects concurrent writes. This is a manual, not autonomous, bridge.

## Catalog schema
```json
{
  "schema": 1,
  "guides": [
    {
      "id": "finance-basics",
      "revision": 1,
      "title": "El primer negocio",
      "summary": "Ingresos, gastos y beneficio.",
      "text": "El beneficio neto se obtiene restando los gastos totales de los ingresos. Una empresa debe considerar transporte y publicidad.",
      "cards": [
        {
          "id": "net-profit",
          "question": "¿Cómo se calcula el beneficio neto de una empresa?",
          "answer": "Se restan todos los gastos de los ingresos totales.",
          "source": "Conceptos básicos de contabilidad",
          "story": "Tu proveedor te ofrece un lote de mercancía. Tu mentor te recuerda que no basta con vender a un precio superior: tienes que cubrir transporte, publicidad y todos los demás gastos."
        }
      ]
    }
  ]
}
```
Use stable IDs and increment each guide's revision for changes. Unchanged card question and answer retain study results. Changed card content resets that card's results; cards omitted from a new revision are retained, and no remote guide is deleted automatically. Keep JSON under 900 KB; large catalogs should be split in a future protocol. Each guide requires usable cards. Story is optional; the adventure player uses it in its scene and narration. The existing player remains a linear episodic challenge, not a full simulation engine. The simulator choice sends a design request only. ChatGPT needs a user conversation or a configured automation to process requests; the app does not call ChatGPT directly.

GitHub stores commit history; deleting a current JSON file does not erase historical copies. Keep the sync repo private. Use an expiring token, and revoke it in GitHub if the phone is lost.
