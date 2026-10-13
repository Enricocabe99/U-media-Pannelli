# 🏗️ Calcolo U media pannelli

App Streamlit per il calcolo della **trasmittanza termica media (U)** di una
serie di pannelli con dimensioni e caratteristiche diverse.

## ✨ Funzionalità

- Inserimento dei pannelli in una tabella editabile (dimensioni in **cm**)
- Navigazione da tastiera: **Invio** per passare alla cella a destra; dall'ultima
  cella dell'ultima riga, **Invio** aggiunge una nuova riga
- Pulsante ❌ per eliminare una singola riga
- Calcolo della **U media pesata sull'area** e della **U media pesata sul numero**
- Import da file Excel nel formato:

  | Pannello | B (cm) | H (cm) | U (W/m²K) | N° |
  |---|---|---|---|---|
  | P1 | 168.0 | 1070 | 0.25 | 2 |
  | P2 | 250.0 | 1070 | 0.23 | 12 |

- Export dei risultati in:
  - 📄 **PDF** (con dettaglio di ogni pannello)
  - 📊 **Excel** (formato re-importabile)
  - 📝 **Testo** (.txt)

## 🚀 Demo online

👉 [Apri l'app su Streamlit Cloud](https://share.streamlit.io/)

## 🖥️ Avvio locale

```bash
git clone https://github.com/TUO-UTENTE/calcolo-u-media-pannelli.git
cd calcolo-u-media-pannelli
pip install -r requirements.txt
streamlit run app.py