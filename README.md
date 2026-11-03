# SD Prompt Assembler — UI v1.0

The repository now includes a React + TypeScript + Vite + Tailwind UI implementation matching the supplied Version 1.0 design brief. The existing Python/Tkinter application remains available; this frontend is an additional UI entrypoint.

## Frontend features

- Reorderable prompt-tag pills and single/multi selection
- Live-compiled output with find-term highlighting
- Undo/redo, weights from 0.1× to 4.0×, presets, nudging, and weight stripping
- Direct tag injection, custom injector-pack editor, and category tag pools
- Save deck tags to a selected category and randomize across available categories
- Persistent prompt library, random prompt picker, and merge
- Case-insensitive find and replace across tag items
- Black / white / lime palette from the supplied spec

The frontend stores deck, pools, packs, and saved prompts in browser `localStorage`; browser security does not permit direct arbitrary writes to `prompt_database.txt`. The existing Python app continues to use local files.

## Run the frontend

```bash
npm install
npm run dev
```

Create a production build with:

```bash
npm run build
```

## Run the existing Python app

```bash
python -m pip install -r requirements.txt
python app.py
```

## Notes

The UI is a client-side app. Tag scraping is not wired to a browser backend in this frontend; use the existing Python app's scraper or add a controlled backend integration. Do not put scraping credentials or unrestricted server-side fetch functionality in a public browser bundle.
