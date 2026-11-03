import React, { useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

type Tag = { id: string; text: string };
type Pack = { name: string; header: string; tags: string };
type Pools = Record<string, string[]>;

const CATEGORIES = ['Actions', 'Environment', 'Clothing (female)', 'Clothing (male)', 'Subject (female)', 'Subject (male)'];
const DEFAULT_POOLS: Pools = {
  Actions: ['standing', 'looking at viewer', 'walking', 'smile'],
  Environment: ['outdoors', 'soft lighting', 'garden'],
  'Clothing (female)': ['dress', 'jacket', 'casual clothes'],
  'Clothing (male)': ['suit', 'shirt', 'casual clothes'],
  'Subject (female)': ['1girl', 'solo'],
  'Subject (male)': ['1boy', 'solo'],
};
const DEFAULT_PACKS: Pack[] = [
  { name: 'Cinematic', header: 'Style', tags: 'cinematic lighting, dramatic composition, depth of field' },
  { name: 'Portrait', header: 'Camera', tags: 'portrait, face focus, upper body, soft background' },
  { name: 'Quality', header: 'Quality', tags: 'masterpiece, highly detailed, best quality' },
];
const key = (name: string) => `sdpa:${name}`;
const id = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
const parseTags = (text: string) => text.split(/[,\n]+/).map((tag) => tag.trim()).filter(Boolean);
const unwrap = (text: string) => text.trim().replace(/^\((.*):\s*\d+(?:\.\d+)?\)$/, '$1');
const weightOf = (text: string) => Number(text.trim().match(/^\(.*:\s*(\d+(?:\.\d+)?)\)$/)?.[1] ?? 1);
const withWeight = (text: string, value: number) => value === 1 ? unwrap(text) : `(${unwrap(text)}:${value.toFixed(2)})`;

function readStorage<T>(name: string, fallback: T): T {
  try { const saved = localStorage.getItem(key(name)); return saved ? JSON.parse(saved) as T : fallback; } catch { return fallback; }
}

function Highlight({ text, term }: { text: string; term: string }) {
  if (!term.trim()) return <>{text}</>;
  const escaped = term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const chunks = text.split(new RegExp(`(${escaped})`, 'ig'));
  return <>{chunks.map((chunk, index) => chunk.toLowerCase() === term.toLowerCase() ? <mark key={index}>{chunk}</mark> : chunk)}</>;
}

function App() {
  const [deck, setDeck] = useState<Tag[]>(() => readStorage('deck', []));
  const [pools, setPools] = useState<Pools>(() => readStorage('pools', DEFAULT_POOLS));
  const [packs, setPacks] = useState<Pack[]>(() => readStorage('packs', DEFAULT_PACKS));
  const [database, setDatabase] = useState<string[]>(() => readStorage('database', []));
  const [selected, setSelected] = useState<string[]>([]);
  const [multiSelect, setMultiSelect] = useState(false);
  const [weight, setWeight] = useState(1);
  const [injectText, setInjectText] = useState('');
  const [findText, setFindText] = useState('');
  const [replaceText, setReplaceText] = useState('');
  const [status, setStatus] = useState('Ready');
  const [modal, setModal] = useState<'packs' | 'database' | null>(null);
  const [draftPacks, setDraftPacks] = useState<Pack[]>(packs);
  const [activePack, setActivePack] = useState(packs[0]?.name ?? '');
  const [category, setCategory] = useState(CATEGORIES[0]);
  const [randomRows, setRandomRows] = useState<string[]>([]);
  const undoRef = useRef<Tag[][]>([]);
  const redoRef = useRef<Tag[][]>([]);
  const dragRef = useRef<string | null>(null);

  useEffect(() => { localStorage.setItem(key('deck'), JSON.stringify(deck)); }, [deck]);
  useEffect(() => { localStorage.setItem(key('pools'), JSON.stringify(pools)); }, [pools]);
  useEffect(() => { localStorage.setItem(key('packs'), JSON.stringify(packs)); }, [packs]);
  useEffect(() => { localStorage.setItem(key('database'), JSON.stringify(database)); }, [database]);

  const output = useMemo(() => deck.map((tag) => tag.text).join(', '), [deck]);
  const changeDeck = (next: Tag[] | ((current: Tag[]) => Tag[])) => {
    undoRef.current.push(deck.map((tag) => ({ ...tag })));
    if (undoRef.current.length > 100) undoRef.current.shift();
    redoRef.current = [];
    setDeck(typeof next === 'function' ? next(deck) : next);
    setSelected([]);
  };
  const addTags = (values: string[]) => {
    const cleaned = values.map((value) => value.trim()).filter(Boolean);
    if (!cleaned.length) return;
    changeDeck((current) => [...current, ...cleaned.map((text) => ({ id: id(), text }))]);
    setStatus(`Added ${cleaned.length} tag${cleaned.length === 1 ? '' : 's'}.`);
  };
  const toggleTag = (tagId: string) => {
    if (multiSelect) setSelected((current) => current.includes(tagId) ? current.filter((value) => value !== tagId) : [...current, tagId]);
    else setSelected((current) => current.includes(tagId) ? [] : [tagId]);
  };
  const updateSelected = (fn: (tag: Tag) => Tag) => {
    if (!selected.length) { setStatus('Select one or more tags first.'); return; }
    changeDeck((current) => current.map((tag) => selected.includes(tag.id) ? fn(tag) : tag));
  };
  const moveTag = (target: string) => {
    const source = dragRef.current;
    dragRef.current = null;
    if (!source || source === target) return;
    changeDeck((current) => {
      const from = current.findIndex((tag) => tag.id === source);
      const to = current.findIndex((tag) => tag.id === target);
      if (from < 0 || to < 0) return current;
      const copy = [...current];
      const [moved] = copy.splice(from, 1);
      copy.splice(to, 0, moved);
      return copy;
    });
  };
  const addWeight = (delta: number) => setWeight((value) => Math.min(4, Math.max(0.1, Math.round((value + delta) * 100) / 100)));
  const saveCategory = () => {
    const values = parseTags(output);
    if (!values.length) { setStatus('The deck is empty.'); return; }
    setPools((current) => ({ ...current, [category]: [...new Set([...(current[category] ?? []), ...values])] }));
    setStatus(`Saved ${values.length} tag(s) to ${category}.`);
  };
  const randomize = () => {
    const selections = CATEGORIES.flatMap((name) => {
      const values = pools[name] ?? [];
      return values.length ? [values[Math.floor(Math.random() * values.length)]] : [];
    });
    if (!selections.length) { setStatus('No category tags are available.'); return; }
    addTags(selections);
  };
  const saveDatabase = () => {
    if (!output.trim()) { setStatus('The deck is empty.'); return; }
    setDatabase((current) => [...current, output]);
    setStatus('Saved current deck to the prompt database.');
  };
  const undo = () => {
    const previous = undoRef.current.pop();
    if (!previous) { setStatus('Nothing to undo.'); return; }
    redoRef.current.push(deck.map((tag) => ({ ...tag })));
    setDeck(previous); setSelected([]); setStatus('Undo complete.');
  };
  const redo = () => {
    const next = redoRef.current.pop();
    if (!next) { setStatus('Nothing to redo.'); return; }
    undoRef.current.push(deck.map((tag) => ({ ...tag })));
    setDeck(next); setSelected([]); setStatus('Redo complete.');
  };
  const findReplace = () => {
    if (!findText) { setStatus('Enter text to find.'); return; }
    let changed = 0;
    changeDeck((current) => current.map((tag) => {
      if (!tag.text.toLowerCase().includes(findText.toLowerCase())) return tag;
      changed++;
      return { ...tag, text: tag.text.replace(new RegExp(findText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'ig'), replaceText) };
    }));
    setStatus(changed ? `Updated ${changed} tag(s).` : 'No matches found.');
  };
  const copy = async () => {
    try { await navigator.clipboard.writeText(output); setStatus('Copied prompt to clipboard.'); }
    catch { setStatus('Clipboard access is unavailable in this browser context.'); }
  };
  const openPacks = () => { setDraftPacks(packs.map((pack) => ({ ...pack }))); setModal('packs'); };
  const savePacks = () => { setPacks(draftPacks.filter((pack) => pack.name.trim())); setActivePack(draftPacks[0]?.name ?? ''); setModal(null); setStatus('Injector packs saved.'); };
  const injectPack = () => {
    const pack = packs.find((item) => item.name === activePack);
    if (pack) addTags(parseTags(pack.tags));
  };

  return <main className="app-shell">
    <header className="topbar"><div className="brand"><span className="brand-mark">✦</span><span>SD PROMPT ASSEMBLER</span></div><div className="top-meta"><span className="live-dot" /> LOCAL WORKSPACE <span className="version">V1.0</span></div></header>
    <section className="workspace">
      <div className="page-heading"><div><p className="eyebrow">CREATIVE TOOLKIT / PROMPT ENGINE</p><h1>Build your <em>visual language.</em></h1><p className="subheading">Arrange, weight, and save prompt tags in one focused workspace.</p></div><div className="heading-actions"><button className="btn btn-quiet" onClick={undo} title="Undo">↶ Undo</button><button className="btn btn-quiet" onClick={redo} title="Redo">↷ Redo</button><button className="btn btn-lime" onClick={copy}>Copy prompt <span>↗</span></button></div></div>

      <section className="panel output-panel"><div className="panel-heading"><div><span className="step">01</span><h2>Live compiled output</h2></div><span className="tiny-label">{output.length} CHARACTERS</span></div><div className="output-box">{output ? <Highlight text={output} term={findText} /> : <span className="placeholder">Your assembled prompt will appear here…</span>}</div></section>

      <section className="panel deck-panel"><div className="panel-heading"><div><span className="step">02</span><h2>Tag assembly deck</h2><span className="count-pill">{deck.length} TAGS</span></div><div className="heading-actions"><button className={`btn ${multiSelect ? 'btn-lime' : 'btn-quiet'}`} onClick={() => { setMultiSelect((value) => !value); setSelected([]); }}>{multiSelect ? '✓ Multi-select on' : 'Multi-select off'}</button><button className="btn btn-quiet" onClick={() => { if (!deck.length) return; changeDeck([]); setStatus('Deck cleared.'); }}>Clear deck</button></div></div>
        <div className="deck-surface">{deck.length === 0 ? <div className="empty-state"><span>＋</span><p>Your deck is empty</p><small>Use direct inject, quick packs, or category randomizer below.</small></div> : deck.map((tag) => <div key={tag.id} draggable onDragStart={() => { dragRef.current = tag.id; }} onDragOver={(event) => event.preventDefault()} onDrop={() => moveTag(tag.id)} onClick={() => toggleTag(tag.id)} className={`tag-pill ${selected.includes(tag.id) ? 'is-selected' : ''}`} title={multiSelect ? 'Click to toggle selection; drag to reorder' : 'Click to select; drag to reorder'}><span className="drag-grip">⠿</span>{Math.abs(weightOf(tag.text) - 1) > 0.001 && <span className="weight-dot" /> }<span className="tag-text"><Highlight text={tag.text} term={findText} /></span>{Math.abs(weightOf(tag.text) - 1) > 0.001 && <span className="weight-badge">×{weightOf(tag.text).toFixed(2)}</span>}<button className="pill-remove" aria-label={`Remove ${tag.text}`} onClick={(event) => { event.stopPropagation(); changeDeck((current) => current.filter((item) => item.id !== tag.id)); }}>×</button></div>)}</div>
        {selected.length > 0 && <div className="selection-note">{selected.length} selected · select a tag again to deselect</div>}
      </section>

      <div className="tool-grid">
        <section className="panel tool-panel inject-panel"><div className="panel-heading"><div><span className="step">03</span><h2>Direct inject</h2></div><span className="tiny-label">SPACE → COMMA</span></div><div className="input-row"><input value={injectText} onChange={(event) => setInjectText(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') { addTags(parseTags(injectText.replace(/\s+/g, ', '))); setInjectText(''); } }} placeholder="Type tags separated by commas or spaces" /><button className="btn btn-lime" onClick={() => { addTags(parseTags(injectText.replace(/\s+/g, ', '))); setInjectText(''); }}>Inject <span>＋</span></button></div><p className="helper">Press Enter or Inject to add tags to the deck.</p></section>

        <section className="panel tool-panel weight-panel"><div className="panel-heading"><div><span className="step">04</span><h2>Weight modifier</h2></div><span className="weight-readout">{weight.toFixed(2)}×</span></div><div className="weight-control"><input type="range" min="0.1" max="4" step="0.05" value={weight} onChange={(event) => setWeight(Number(event.target.value))} /><div className="nudge-buttons"><button className="btn btn-square" onClick={() => addWeight(-0.05)}>−</button><button className="btn btn-square" onClick={() => addWeight(0.05)}>＋</button></div></div><div className="preset-row">{[0.5, 0.7, 1, 1.1, 1.2, 1.3, 1.5].map((value) => <button key={value} className="preset" onClick={() => setWeight(value)}>{value.toFixed(1)}×</button>)}</div><div className="action-row"><button className="btn btn-lime" onClick={() => updateSelected((tag) => ({ ...tag, text: withWeight(tag.text, weight) }))}>Apply to selected</button><button className="btn btn-quiet" onClick={() => updateSelected((tag) => ({ ...tag, text: unwrap(tag.text) }))}>Strip weight</button></div></section>

        <section className="panel tool-panel injector-panel"><div className="panel-heading"><div><span className="step">05</span><h2>Quick injectors</h2></div><button className="icon-button" onClick={openPacks} title="Manage tag packs">⚙</button></div><div className="injector-row"><select value={activePack} onChange={(event) => setActivePack(event.target.value)}>{packs.length === 0 && <option value="">No packs yet</option>}{packs.map((pack) => <option key={pack.name} value={pack.name}>{pack.header} / {pack.name}</option>)}</select><button className="btn btn-lime" onClick={injectPack} disabled={!packs.length}>Inject pack <span>＋</span></button></div><div className="category-row"><select value={category} onChange={(event) => setCategory(event.target.value)}>{CATEGORIES.map((name) => <option key={name}>{name}</option>)}</select><button className="btn btn-quiet" onClick={saveCategory}>Save to category</button><button className="btn btn-quiet" onClick={randomize}>Randomize all</button></div><p className="helper">Category pools and injector packs persist in this browser.</p></section>

        <section className="panel tool-panel search-panel"><div className="panel-heading"><div><span className="step">06</span><h2>Search &amp; replace</h2></div><span className="tiny-label">HIGHLIGHT + BATCH EDIT</span></div><div className="search-fields"><input value={findText} onChange={(event) => setFindText(event.target.value)} placeholder="Find / highlight text" /><input value={replaceText} onChange={(event) => setReplaceText(event.target.value)} placeholder="Replace with" /><button className="btn btn-lime" onClick={findReplace}>Replace all</button></div><p className="helper">Matches highlight in the output and deck. Replace edits every matching tag.</p></section>

        <section className="panel tool-panel database-panel"><div className="panel-heading"><div><span className="step">07</span><h2>Prompt library</h2></div><span className="tiny-label">{database.length} SAVED</span></div><div className="action-row"><button className="btn btn-quiet" onClick={saveDatabase}>Save deck to database</button><button className="btn btn-lime" onClick={() => { setRandomRows(database); setModal('database'); }}>Open randomizer <span>↗</span></button></div><p className="helper">Saved locally in your browser storage.</p></section>
      </div>
    </section>
    <footer className="statusbar"><span className="status-indicator" />{status}<span className="status-right">LOCAL DATA · AUTOSAVED</span></footer>

    {modal === 'packs' && <div className="modal-backdrop" onClick={() => setModal(null)}><section className="modal" onClick={(event) => event.stopPropagation()}><div className="modal-heading"><div><p className="eyebrow">CUSTOM INJECTOR BUILDER</p><h2>Manage tag packs</h2></div><button className="icon-button" onClick={() => setModal(null)}>×</button></div><div className="pack-list">{draftPacks.map((pack, index) => <div className="pack-editor" key={`${index}-${pack.name}`}><input aria-label="Pack header" value={pack.header} placeholder="Pack header" onChange={(event) => setDraftPacks((current) => current.map((item, i) => i === index ? { ...item, header: event.target.value } : item))} /><input aria-label="Pack name" value={pack.name} placeholder="Pack name" onChange={(event) => setDraftPacks((current) => current.map((item, i) => i === index ? { ...item, name: event.target.value } : item))} /><textarea aria-label="Pack tags" value={pack.tags} placeholder="Comma-separated tags" onChange={(event) => setDraftPacks((current) => current.map((item, i) => i === index ? { ...item, tags: event.target.value } : item))} /><button className="btn btn-danger" onClick={() => setDraftPacks((current) => current.filter((_, i) => i !== index))}>Remove</button></div>)}</div><div className="modal-actions"><button className="btn btn-quiet" onClick={() => setDraftPacks((current) => [...current, { name: '', header: 'Custom', tags: '' }])}>＋ Add pack</button><button className="btn btn-lime" onClick={savePacks}>Save packs</button></div></section></div>}

    {modal === 'database' && <div className="modal-backdrop" onClick={() => setModal(null)}><section className="modal database-modal" onClick={(event) => event.stopPropagation()}><div className="modal-heading"><div><p className="eyebrow">LOCAL PROMPT DATABASE</p><h2>Randomizer</h2></div><button className="icon-button" onClick={() => setModal(null)}>×</button></div>{database.length === 0 ? <p className="helper">No saved prompts yet. Save a deck to build your library.</p> : <><p className="helper">Choose one or more saved prompts to merge into the deck.</p><div className="saved-list">{database.map((row, index) => <label key={`${index}-${row}`}><input type="checkbox" checked={randomRows.includes(row)} onChange={(event) => setRandomRows((current) => event.target.checked ? [...current, row] : current.filter((item) => item !== row))} /><span>{row}</span></label>)}</div><div className="modal-actions"><button className="btn btn-quiet" onClick={() => setRandomRows(database.length ? [database[Math.floor(Math.random() * database.length)]] : [])}>Pick random one</button><button className="btn btn-lime" onClick={() => { addTags(randomRows.flatMap(parseTags)); setModal(null); }}>Merge selected</button></div></>}</section></div>}
  </main>;
}

createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>);
