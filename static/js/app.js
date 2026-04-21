let resultId, resultFile;

function showMode(mode) {
    document.getElementById('modeSelect').style.display = 'none';
    document.getElementById(mode + 'Mode').style.display = 'block';
}

function back() {
    document.getElementById('csvMode').style.display = 'none';
    document.getElementById('mergeMode').style.display = 'none';
    document.getElementById('modeSelect').style.display = 'block';
}

document.getElementById('mmeFile')?.addEventListener('change', e => {
    document.getElementById('mmeName').textContent = e.target.files[0]?.name || '';
});

document.getElementById('csvFile')?.addEventListener('change', e => {
    document.getElementById('csvName').textContent = e.target.files[0]?.name || '';
});

document.getElementById('mmeFiles')?.addEventListener('change', e => {
    const names = Array.from(e.target.files).map(f => f.name).join(', ');
    document.getElementById('mmesName').textContent = names;
});

async function processCSV() {
    const mme = document.getElementById('mmeFile').files[0];
    const csv = document.getElementById('csvFile').files[0];
    if (!mme || !csv) return alert('Sélectionnez les fichiers');
    
    const form = new FormData();
    form.append('mmeFile', mme);
    form.append('csvFile', csv);
    form.append('settings', '{}');
    
    document.getElementById('loading').style.display = 'block';
    
    try {
        const res = await fetch('/api/add-csv', { method: 'POST', body: form });
        const data = await res.json();
        
        if (data.success) {
            resultId = data.resultId;
            resultFile = data.filename;
            document.getElementById('csvResults').innerHTML = `
                <div class="results">
                    <h3>✓ Terminé</h3>
                    <p>Voies ajoutées: ${data.stats.channelsAdded}</p>
                    <p>Total canaux: ${data.stats.totalChannels}</p>
                    <button onclick="download()" class="btn-download">Télécharger</button>
                </div>
            `;
        } else {
            alert('Erreur: ' + data.error);
        }
    } catch(e) {
        alert('Erreur: ' + e.message);
    }
    
    document.getElementById('loading').style.display = 'none';
}

async function processMerge() {
    const files = document.getElementById('mmeFiles').files;
    if (files.length < 2) return alert('Au moins 2 fichiers');
    
    const form = new FormData();
    Array.from(files).forEach(f => form.append('mmeFiles', f));
    
    document.getElementById('loading').style.display = 'block';
    
    try {
        const res = await fetch('/api/merge', { method: 'POST', body: form });
        const data = await res.json();
        
        if (data.success) {
            resultId = data.resultId;
            resultFile = data.filename;
            document.getElementById('mergeResults').innerHTML = `
                <div class="results">
                    <h3>✓ Terminé</h3>
                    <p>Fichiers fusionnés: ${data.stats.filesMerged}</p>
                    <p>Total canaux: ${data.stats.totalChannels}</p>
                    <button onclick="download()" class="btn-download">Télécharger</button>
                </div>
            `;
        } else {
            alert('Erreur: ' + data.error);
        }
    } catch(e) {
        alert('Erreur: ' + e.message);
    }
    
    document.getElementById('loading').style.display = 'none';
}

function download() {
    if (resultId && resultFile) {
        window.location.href = `/api/download/${resultId}/${resultFile}`;
    }
}

async function quit() {
    if (confirm('Quitter?')) {
        try {
            await fetch('/api/shutdown', { method: 'POST' });
        } catch(e) {}
        document.body.innerHTML = '<div style="text-align:center;padding:4rem"><h1>✓ Fermé</h1></div>';
        setTimeout(() => window.close(), 1000);
    }
}
