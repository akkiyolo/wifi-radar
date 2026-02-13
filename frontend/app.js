import * as THREE from 'https://unpkg.com/three@0.166.1/build/three.module.js';
import { OrbitControls } from 'https://unpkg.com/three@0.166.1/examples/jsm/controls/OrbitControls.js';

const canvas = document.getElementById('scene');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

const scene = new THREE.Scene();
scene.fog = new THREE.FogExp2(0x020409, 0.032);

const camera = new THREE.PerspectiveCamera(65, window.innerWidth / window.innerHeight, 0.1, 200);
camera.position.set(0, 10, 22);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;

scene.add(new THREE.AmbientLight(0x4affcf, 0.6));
const dir = new THREE.DirectionalLight(0x80ffd8, 0.8);
dir.position.set(4, 8, 6);
scene.add(dir);

const grid = new THREE.GridHelper(80, 80, 0x123f3b, 0x0b2221);
grid.position.y = -12;
scene.add(grid);

const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();

const nodeObjects = new Map();
const labels = new Map();
let edgeLines = [];
let snapshot = { nodes: [], edges: [], positions: {} };
let paused = false;

const inspectEl = document.getElementById('inspect');
const toggleLabels = document.getElementById('toggleLabels');
const minRssiEl = document.getElementById('minRssi');
const bandFilterEl = document.getElementById('bandFilter');
const pauseBtn = document.getElementById('pauseBtn');

let socket = null;
let demoMode = false;

function startDemoMode() {
  if (demoMode) return;
  demoMode = true;
  const seeds = [
    { id: 'AA:11:22:33:44:01', ssid: 'NEO-MESH', band: '2.4GHz', security: 'WPA2' },
    { id: 'AA:11:22:33:44:02', ssid: 'ZION-HUB', band: '2.4GHz', security: 'WPA2' },
    { id: 'AA:11:22:33:44:03', ssid: 'MATRIX-NODE', band: '2.4GHz', security: 'WPA3' },
    { id: 'AA:11:22:33:44:04', ssid: 'SENTINEL-5G', band: '5GHz', security: 'WPA2' },
    { id: 'AA:11:22:33:44:05', ssid: 'ORACLE-LINK', band: '5GHz', security: 'OPEN' },
  ];
  inspectEl.textContent = 'Preview mode: backend websocket unavailable. Showing synthetic stream.';
  let t = 0;
  setInterval(() => {
    if (paused) return;
    t += 0.2;
    const nodes = seeds.map((n, i) => ({
      ...n,
      bssid: n.id,
      rssi: -62 + Math.sin(t + i * 0.7) * 10 + Math.sin(t * 0.4 + i) * 4,
      channel: null,
      frequency: n.band === '5GHz' ? 5180 + i * 20 : 2412 + i * 5,
    }));
    const positions = {};
    nodes.forEach((n, i) => {
      positions[n.id] = [
        Math.cos(t * 0.4 + i * 1.2) * (6 + i * 0.6),
        Math.sin(t * 0.7 + i) * 2.5,
        Math.sin(t * 0.35 + i * 0.8) * (6 + i * 0.5),
      ];
    });
    const edges = [];
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const corr = 0.5 + 0.5 * Math.sin(t + i * 0.5 + j * 0.3);
        if (corr > 0.3) edges.push({ source: nodes[i].id, target: nodes[j].id, corr });
      }
    }
    snapshot = { type: 'snapshot', nodes, edges, positions };
    syncScene();
  }, 900);
}

try {
  socket = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`);
  socket.onmessage = (event) => {
    const packet = JSON.parse(event.data);
    if (packet.type === 'snapshot') {
      snapshot = packet;
      syncScene();
    }
  };
  socket.onerror = () => startDemoMode();
  socket.onclose = () => startDemoMode();
  setTimeout(() => {
    if (!snapshot.nodes.length) startDemoMode();
  }, 2500);
} catch (_e) {
  startDemoMode();
}

pauseBtn.onclick = () => {
  paused = !paused;
  pauseBtn.textContent = paused ? 'Resume' : 'Pause';
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ type: 'pause', value: paused }));
  }
};

function shouldRenderNode(node) {
  const minRssi = Number(minRssiEl.value);
  const band = bandFilterEl.value;
  if (node.rssi < minRssi) return false;
  if (band !== 'all' && node.band !== band) return false;
  return true;
}

function nodeColor(rssi) {
  const t = Math.max(0, Math.min(1, (rssi + 95) / 65));
  return new THREE.Color().setHSL(0.35 + t * 0.1, 1.0, 0.45 + t * 0.2);
}

function createNode(node) {
  const geo = new THREE.SphereGeometry(0.45, 18, 18);
  const mat = new THREE.MeshStandardMaterial({
    color: nodeColor(node.rssi),
    emissive: nodeColor(node.rssi),
    emissiveIntensity: 1.2,
    metalness: 0.1,
    roughness: 0.2,
  });
  const mesh = new THREE.Mesh(geo, mat);
  mesh.userData.nodeId = node.id;
  scene.add(mesh);
  nodeObjects.set(node.id, mesh);

  const label = document.createElement('div');
  label.className = 'label';
  label.textContent = `${node.ssid} (${node.rssi.toFixed(0)} dBm)`;
  document.body.appendChild(label);
  labels.set(node.id, label);
}

function syncScene() {
  const valid = new Set(snapshot.nodes.filter(shouldRenderNode).map((n) => n.id));

  for (const node of snapshot.nodes) {
    if (!shouldRenderNode(node)) continue;
    if (!nodeObjects.has(node.id)) createNode(node);
    const mesh = nodeObjects.get(node.id);
    const p = snapshot.positions[node.id] || [0, 0, 0];
    mesh.position.set(p[0], p[1], p[2]);
    mesh.material.color = nodeColor(node.rssi);
    mesh.material.emissive = nodeColor(node.rssi);
    const label = labels.get(node.id);
    label.textContent = `${node.ssid} (${node.rssi.toFixed(0)} dBm)`;
    label.style.display = toggleLabels.checked ? 'block' : 'none';
  }

  for (const [id, mesh] of nodeObjects.entries()) {
    if (!valid.has(id)) {
      scene.remove(mesh);
      nodeObjects.delete(id);
      const label = labels.get(id);
      label?.remove();
      labels.delete(id);
    }
  }

  for (const e of edgeLines) scene.remove(e);
  edgeLines = [];
  for (const edge of snapshot.edges) {
    if (!valid.has(edge.source) || !valid.has(edge.target)) continue;
    const a = snapshot.positions[edge.source];
    const b = snapshot.positions[edge.target];
    if (!a || !b) continue;
    const points = [new THREE.Vector3(...a), new THREE.Vector3(...b)];
    const geo = new THREE.BufferGeometry().setFromPoints(points);
    const mat = new THREE.LineBasicMaterial({ color: 0x25ffcb, transparent: true, opacity: Math.max(0.15, edge.corr) });
    const line = new THREE.Line(geo, mat);
    scene.add(line);
    edgeLines.push(line);
  }
}

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

window.addEventListener('click', (event) => {
  mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
  mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;
  raycaster.setFromCamera(mouse, camera);
  const hits = raycaster.intersectObjects([...nodeObjects.values()]);
  if (!hits.length) return;
  const id = hits[0].object.userData.nodeId;
  const node = snapshot.nodes.find((n) => n.id === id);
  if (!node) return;
  const peers = snapshot.edges
    .filter((e) => e.source === id || e.target === id)
    .map((e) => `${e.source === id ? e.target : e.source}: r=${e.corr.toFixed(2)}`)
    .join('\n');
  inspectEl.textContent = [
    `SSID: ${node.ssid}`,
    `BSSID: ${node.bssid}`,
    `RSSI: ${node.rssi.toFixed(1)} dBm`,
    `Band: ${node.band}`,
    `Security: ${node.security}`,
    '',
    'Correlations:',
    peers || 'None > 0.3 yet',
  ].join('\n');
});

function animate() {
  controls.update();
  for (const [id, label] of labels.entries()) {
    const mesh = nodeObjects.get(id);
    if (!mesh) continue;
    const v = mesh.position.clone().project(camera);
    const x = (v.x * 0.5 + 0.5) * window.innerWidth;
    const y = (-v.y * 0.5 + 0.5) * window.innerHeight;
    label.style.transform = `translate(${x}px, ${y}px)`;
    label.style.opacity = v.z < 1 ? '0.9' : '0';
  }
  renderer.render(scene, camera);
  requestAnimationFrame(animate);
}
animate();
