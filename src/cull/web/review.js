"use strict";

// The keys listed in the footer, one set for each view
const HINTS = {
  grid: [["Arrows", "Move"], ["P", "Pick"], ["X", "Reject"], ["U", "Clear"], ["A", "Accept group"], ["Tab", "Next group"],
         ["N", "Next undecided"], ["Enter", "Open"], ["C", "Compare"], ["Ctrl+Z", "Undo"]],
  single: [["← →", "Previous, next"], ["P", "Pick"], ["X", "Reject"], ["U", "Clear"], ["A", "Accept group"], ["Tab", "Next group"],
           ["Z", "Zoom 100%"], ["Shift+Arrows", "Pan"], ["C", "Compare"], ["Esc", "Back to grid"]],
  compare: [["← →", "Change right photo"], ["P", "Pick right"], ["X", "Reject right"], ["U", "Clear right"], ["S", "Keep right, move it left"],
            ["A", "Pick left, reject the rest"], ["Tab", "Next group"], ["Z", "Zoom 100%"], ["Shift+Arrows", "Pan both"], ["Esc", "Back to grid"]],
};

const PAN_STEP = 0.1; // Of the photo's size
const RETRY_AFTER = 3000; // Milliseconds
const NOTICE_FOR = 3000; // Milliseconds

const $ = id => document.getElementById(id);
const panes = [$("held"), $("active")].map(element => ({
  element, image: element.querySelector("img"), caption: element.querySelector("figcaption"), photo: null, sharp: false,
}));
const [heldPane, activePane] = panes;

let run = "";
let autoAdvance = true;
let sections = [];
let photos = []; // Every photo in the order they're reviewed
let focus = null;
let viewing = false; // The viewer is open
let held = null; // The photo on the left of the compare view, null when not comparing
let zoomed = false;
let pan = { x: 0.5, y: 0.5 }; // The spot in the middle of a zoomed view, both sides show the same spot

const undoList = [];
const unsaved = new Map(); // id to decision, kept until the server says they're on disk
let sending = false;
let noticeTimer = null;

const thumbUrl = photo => `/photos/${photo.id}/thumb?v=${run}`;
const fullUrl = photo => `/photos/${photo.id}/full?v=${run}`;
const clamp = (value, low, high) => Math.min(Math.max(value, low), high);


// Building the page. File names go in through textContent, so a name can never be read as HTML

function makeTile(photo) {
  const tile = document.createElement("div");
  const image = document.createElement("img");
  const mark = document.createElement("span");
  const star = document.createElement("span");
  const name = document.createElement("p");
  const label = document.createElement("bdi"); // Keeps the characters of the name in order, the CSS below reverses the line

  tile.className = "tile";
  image.loading = "lazy";
  image.decoding = "async";
  image.alt = "";
  image.src = thumbUrl(photo);
  image.addEventListener("error", () => tile.classList.add("missing"));
  mark.className = "mark";
  star.className = "star";
  label.textContent = photo.name;
  name.append(label);
  name.title = photo.name;

  if (photo.section.suggested === photo.id) {
    tile.classList.add("suggested");
    star.textContent = "★ Suggested";
  }

  tile.append(image, mark, star, name);
  tile.addEventListener("click", () => go(photo));
  tile.addEventListener("dblclick", openViewer);
  return tile;
}

function build(shoot) {
  run = shoot.run;
  autoAdvance = shoot.autoAdvance;
  sections = shoot.sections;
  $("shoot").textContent = shoot.name;
  document.title = `${shoot.name} · Cull`;

  sections.forEach((section, number) => {
    const block = document.createElement("section");
    const heading = document.createElement("h2");
    const count = document.createElement("span");
    const tiles = document.createElement("div");

    section.number = number;
    section.block = block;
    section.count = count;
    section.tiles = tiles;
    block.className = "group";
    tiles.className = "tiles";
    heading.append(section.kind, count);
    block.append(heading, tiles);

    section.photos.forEach((photo, index) => {
      photo.section = section;
      photo.index = index;
      photo.place = photos.length;
      photo.decision = shoot.decisions[photo.id] ?? null;
      photo.tile = makeTile(photo);
      photos.push(photo);
      tiles.append(photo.tile);
      paintTile(photo);
    });

    section.suggestedPhoto = section.photos.find(photo => photo.id === section.suggested) ?? null;
    paintSection(section);
    $("grid").append(block);
  });
}


// Drawing what's changed

function paintTile(photo) {
  photo.tile.classList.toggle("pick", photo.decision === "pick");
  photo.tile.classList.toggle("reject", photo.decision === "reject");
  photo.tile.querySelector(".mark").textContent = { pick: "✓ PICK", reject: "✕ REJECT" }[photo.decision] ?? "";
}

function paintSection(section) {
  const total = section.photos.length;
  const decided = section.photos.filter(photo => photo.decision).length;
  section.count.textContent = `${total} photo${total === 1 ? "" : "s"}, ${decided} decided`;
  section.block.classList.toggle("done", decided === total);
}

function paintProgress() {
  const picks = photos.filter(photo => photo.decision === "pick").length;
  const rejects = photos.filter(photo => photo.decision === "reject").length;
  const decided = picks + rejects;
  $("progress").textContent = `${decided} of ${photos.length} decided, ${picks} picks, ${rejects} rejects`;
  $("meter").firstElementChild.style.width = `${decided / photos.length * 100}%`;
}

function paintDetails() {
  const scores = [`${focus.index + 1} of ${focus.section.photos.length} in ${focus.section.kind}`,
                  `Sharpness ${focus.sharpness.toFixed(1)}`];
  if (focus.beats !== null) {
    scores.push(`beats ${focus.beats.toFixed(0)}% of the shoot`);
  }
  scores.push(`${focus.clipped.toFixed(1)}% clipped`);
  if (focus.taken) {
    scores.push(focus.taken.slice(0, 19).replace("T", " "));
  }
  $("name").textContent = focus.name;
  $("scores").textContent = scores.join(", ");
  $("reason").textContent = focus.reason;
}

function paintKeys() {
  const keys = $("keys");
  keys.replaceChildren();
  for (const [key, action] of HINTS[held ? "compare" : viewing ? "single" : "grid"]) {
    const hint = document.createElement("span");
    const label = document.createElement("kbd");
    label.textContent = key;
    hint.append(label, ` ${action}`);
    keys.append(hint);
  }
}

// Places a photo at 100%, one pixel of the photo to one pixel of the screen
function placeImage(pane) {
  const { image, element } = pane;
  const actual = zoomed && pane.sharp;
  image.classList.toggle("actual", actual);
  if (!actual) {
    image.removeAttribute("style");
    return;
  }

  const width = image.naturalWidth / devicePixelRatio;
  const height = image.naturalHeight / devicePixelRatio;
  const box = element.getBoundingClientRect();
  const left = width > box.width ? clamp(box.width / 2 - pan.x * width, box.width - width, 0) : (box.width - width) / 2;
  const top = height > box.height ? clamp(box.height / 2 - pan.y * height, box.height - height, 0) : (box.height - height) / 2;
  image.style.width = `${width}px`;
  image.style.height = `${height}px`;
  image.style.transform = `translate(${left}px, ${top}px)`;
}

// The thumbnail is already loaded, so it shows straight away until the full photo arrives. While zoomed the
// old photo stays up instead, jumping out to the whole frame would lose the spot being compared
function paintPane(pane, photo, label) {
  pane.element.hidden = !photo;
  if (!photo) {
    pane.photo = null;
    pane.sharp = false;
    pane.image.removeAttribute("src");
    return;
  }

  const mark = { pick: "Pick", reject: "Rejected" }[photo.decision];
  pane.element.classList.toggle("pick", photo.decision === "pick");
  pane.element.classList.toggle("reject", photo.decision === "reject");
  pane.caption.textContent = [label, photo.name, mark, photo.section.suggestedPhoto === photo ? "Suggested" : ""].filter(Boolean).join(" · ");

  if (pane.photo === photo) {
    placeImage(pane);
    return;
  }

  const showThumb = () => {
    pane.sharp = false;
    pane.image.src = thumbUrl(photo);
    placeImage(pane);
  };

  pane.photo = photo;
  if (!zoomed) {
    showThumb();
  }

  const loader = new Image();
  loader.addEventListener("load", () => {
    if (pane.photo === photo) { // Skip past a photo quickly and this load is out of date
      pane.sharp = true;
      pane.image.src = loader.src;
    }
  });
  loader.addEventListener("error", () => {
    if (pane.photo === photo) {
      showThumb();
    }
  });
  loader.src = fullUrl(photo);
}

function paintViewer() {
  $("viewer").hidden = !viewing;
  paintKeys();
  if (!viewing) {
    return;
  }

  paintPane(heldPane, held, "Left");
  paintPane(activePane, focus, held ? "Right" : "");

  // Loads the neighbors early, so stepping through a group doesn't wait
  for (const photo of [photos[focus.place + 1], photos[focus.place - 1]]) {
    if (photo) {
      new Image().src = fullUrl(photo);
    }
  }
}

function notice(text) {
  const status = $("status");
  if (status.classList.contains("error")) { // Never hides a warning that decisions aren't saved
    return;
  }
  status.textContent = text;
  clearTimeout(noticeTimer);
  noticeTimer = setTimeout(() => { status.textContent = ""; }, NOTICE_FOR);
}

function showError(text) {
  $("status").textContent = text;
  $("status").classList.add("error");
}

function clearError() {
  $("status").textContent = "";
  $("status").classList.remove("error");
}


// Saving. One request at a time so they can't arrive out of order, anything that fails is tried again

async function flush() {
  if (sending) {
    return;
  }
  sending = true;

  while (unsaved.size) {
    const batch = [...unsaved];
    unsaved.clear();
    try {
      const response = await fetch("/api/decisions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ changes: batch.map(([id, decision]) => ({ id, decision })) }),
      }).catch(() => { throw new Error("Cull isn't answering, is cull review still running?"); });
      if (!response.ok) {
        throw new Error((await response.json()).detail);
      }
      clearError();
    } catch (error) {
      for (const [id, decision] of batch) {
        if (!unsaved.has(id)) { // A newer decision on the same photo wins
          unsaved.set(id, decision);
        }
      }
      showError(`Decisions aren't saved, trying again. ${error.message}`);
      sending = false;
      setTimeout(flush, RETRY_AFTER);
      return;
    }
  }
  sending = false;
}

// Takes [photo, decision] pairs
function decide(changes, remember = true) {
  const real = changes.filter(([photo, decision]) => photo.decision !== decision);
  if (!real.length) {
    return;
  }
  if (remember) {
    undoList.push(real.map(([photo]) => [photo, photo.decision]));
  }

  for (const [photo, decision] of real) {
    photo.decision = decision;
    unsaved.set(photo.id, decision);
    paintTile(photo);
    paintSection(photo.section);
  }
  paintProgress();
  paintViewer();
  flush();
}


// Moving around

function go(photo) {
  if (!photo) {
    return;
  }
  focus?.tile.classList.remove("focus");
  focus = photo;
  photo.tile.classList.add("focus");
  photo.tile.scrollIntoView({ block: "nearest" });
  paintDetails();
  paintViewer();
}

// While comparing, the right side steps through the rest of the group
function step(direction) {
  if (!held) {
    go(photos[focus.place + direction]);
    return;
  }
  const others = focus.section.photos.filter(photo => photo !== held);
  go(others[others.indexOf(focus) + direction]);
}

// Up and down keep the same column, and carry on into the group above or below
function moveRow(direction) {
  const section = focus.section;
  const total = section.photos.length;
  const columns = getComputedStyle(section.tiles).gridTemplateColumns.split(" ").length;
  const column = focus.index % columns;
  const target = focus.index + direction * columns;

  if (target >= 0 && target < total) {
    go(section.photos[target]);
  } else if (direction > 0 && Math.floor(focus.index / columns) < Math.floor((total - 1) / columns)) {
    go(section.photos[total - 1]); // The last row is short and this column has no photo in it
  } else if (direction > 0) {
    const below = sections[section.number + 1];
    go(below?.photos[Math.min(column, below.photos.length - 1)]);
  } else {
    const above = sections[section.number - 1];
    if (above) {
      const lastRow = Math.floor((above.photos.length - 1) / columns) * columns;
      go(above.photos[Math.min(lastRow + column, above.photos.length - 1)]);
    }
  }
}

function enterGroup(section) {
  if (!section) {
    notice("No more groups");
    return;
  }
  const comparing = held && section.photos.length > 1;
  held = null;
  go(section.photos[0]);
  if (comparing) {
    openCompare();
  }
}

function nextUndecided() {
  const after = [...photos.slice(focus.place + 1), ...photos.slice(0, focus.place)];
  const found = after.find(photo => !photo.decision);
  if (found) {
    held = null;
    go(found);
  } else {
    notice(focus.decision ? "Every photo has a decision" : "This is the last undecided photo");
  }
}


// Decisions

function mark(decision) {
  const next = focus.decision === decision ? null : decision; // Pressing the same key again takes it back
  decide([[focus, next]]);
  if (next && autoAdvance) {
    step(1);
  }
}

// Fills in whatever the photographer hasn't decided, and never changes what they have
function finishGroup() {
  const section = focus.section;
  if (!section.suggestedPhoto) { // Singles have nothing in common, one key must never reject all of them
    notice("These photos aren't a group, so each one needs its own decision");
    return;
  }

  const chosen = held ?? section.suggestedPhoto;
  const hasPick = section.photos.some(photo => photo.decision === "pick");
  const pickChosen = held || !hasPick; // In the compare view the left photo is a choice made just now
  decide(section.photos.filter(photo => !photo.decision)
                       .map(photo => [photo, photo === chosen && pickChosen ? "pick" : "reject"]));
  enterGroup(sections[section.number + 1]);
}

function undoLast() {
  const last = undoList.pop();
  if (!last) {
    notice("Nothing to undo");
    return;
  }
  held = null;
  decide(last, false);
  go(last[0][0]);
}


// The viewer

function openViewer() {
  viewing = true;
  paintViewer();
}

function closeViewer() {
  viewing = false;
  held = null;
  zoomed = false;
  pan = { x: 0.5, y: 0.5 };
  paintViewer();
}

// Starts with the photo most likely to be kept on the left, and the rest of the group steps past it on the right
function openCompare() {
  const section = focus.section;
  if (section.photos.length < 2) {
    notice("There's nothing to compare this photo with");
    return;
  }
  held = section.photos.find(photo => photo.decision === "pick") ?? section.suggestedPhoto ?? focus;
  viewing = true;
  go(focus === held ? section.photos.find(photo => photo !== held) : focus);
}

function toggleCompare() {
  if (held) {
    held = null;
    paintViewer();
  } else {
    openCompare();
  }
}

function swap() {
  if (held) {
    const left = held;
    held = focus;
    go(left);
  }
}

function toggleZoom() {
  if (viewing) {
    zoomed = !zoomed;
    panes.forEach(placeImage);
  }
}

function movePan(x, y) {
  if (zoomed) {
    pan = { x: clamp(pan.x + x * PAN_STEP, 0, 1), y: clamp(pan.y + y * PAN_STEP, 0, 1) };
    panes.forEach(placeImage);
  }
}


// Keys

const KEYS = {
  ArrowLeft: () => step(-1),
  ArrowRight: () => step(1),
  ArrowUp: () => viewing || moveRow(-1),
  ArrowDown: () => viewing || moveRow(1),
  Tab: event => enterGroup(sections[focus.section.number + (event.shiftKey ? -1 : 1)]),
  Enter: () => (viewing ? closeViewer() : openViewer()),
  Escape: () => viewing && closeViewer(),
  p: () => mark("pick"),
  x: () => mark("reject"),
  u: () => decide([[focus, null]]),
  a: finishGroup,
  n: nextUndecided,
  c: toggleCompare,
  s: swap,
  z: toggleZoom,
};

const PAN_KEYS = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] };

document.addEventListener("keydown", event => {
  if (!focus || event.altKey || event.metaKey) {
    return;
  }
  const key = event.key.length === 1 ? event.key.toLowerCase() : event.key;

  if (event.ctrlKey) { // Leaves the browser's own shortcuts working
    if (key === "z") {
      event.preventDefault();
      undoLast();
    }
    return;
  }

  if (viewing && event.shiftKey && PAN_KEYS[key]) {
    event.preventDefault();
    movePan(...PAN_KEYS[key]);
    return;
  }

  if (KEYS[key]) {
    event.preventDefault();
    if (!event.repeat || key.startsWith("Arrow")) { // Holding P mustn't run through the whole shoot
      KEYS[key](event);
    }
  }
});

panes.forEach(pane => pane.image.addEventListener("load", () => placeImage(pane)));
addEventListener("resize", () => panes.forEach(placeImage));
addEventListener("beforeunload", event => {
  if (sending || unsaved.size) {
    event.preventDefault();
  }
});


async function start() {
  try {
    const response = await fetch("/api/shoot");
    build(await response.json());
  } catch (error) {
    showError(`Couldn't load the shoot: ${error.message}`);
    return;
  }
  paintProgress();
  paintKeys();
  go(photos.find(photo => !photo.decision) ?? photos[0]);
}

start();
