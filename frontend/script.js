document.addEventListener('DOMContentLoaded', () => {
    // Elements: Upload / Main
    const analyzeBtn = document.getElementById('analyze-btn');
    const uploadSection = document.getElementById('upload-section');
    const processingSection = document.getElementById('processing-section');
    const resultSection = document.getElementById('result-section');
    const dataDisplay = document.getElementById('data-display');
    const generateBtn = document.getElementById('generate-btn');
    const downloadArea = document.getElementById('download-area');
    const fileInput = document.getElementById('file-input');
    const dropZone = document.getElementById('drop-zone');
    const textInput = document.getElementById('text-input');
    const selectionStatus = document.getElementById('selection-status');
    const progressBar = document.getElementById('progress-bar');
    const projectList = document.getElementById('project-list');

    // Elements: Settings & Rules
    const customApiKeyInput = document.getElementById('custom-api-key');
    const saveSettingsBtn = document.getElementById('save-settings-btn');
    const ruleModal = document.getElementById('rule-modal');
    const addRuleBtn = document.getElementById('add-rule-modal-btn');
    const closeModalBtn = document.getElementById('close-modal-btn');
    const submitRuleBtn = document.getElementById('submit-rule-btn');
    const ruleInput = document.getElementById('rule-input');
    const ruleStatus = document.getElementById('rule-status');

    let currentInquiryId = null;
    let currentData = null; // Holds the nested JSON

    // Optional API Key save feedback
    saveSettingsBtn.addEventListener('click', () => {
        saveSettingsBtn.innerHTML = "✅";
        saveSettingsBtn.style.color = "lightgreen";
        setTimeout(() => { 
            saveSettingsBtn.innerHTML = "⚙️"; 
            saveSettingsBtn.style.color = ""; 
        }, 2000);
    });

    // Modal Logic
    addRuleBtn.addEventListener('click', () => {
        ruleModal.classList.remove('hidden');
        ruleStatus.classList.add('hidden');
        ruleInput.value = '';
    });
    closeModalBtn.addEventListener('click', () => ruleModal.classList.add('hidden'));

    submitRuleBtn.addEventListener('click', async () => {
        const ruleText = ruleInput.value.trim();
        if(!ruleText) return;

        submitRuleBtn.innerText = "Saving...";
        try {
            const formData = new FormData();
            formData.append('rule', ruleText);
            const response = await fetch('/add_rule', { method: 'POST', body: formData });
            if(response.ok) {
                ruleStatus.innerHTML = "✅ Rule added successfully to AI memory!";
                ruleStatus.classList.remove('hidden');
                ruleStatus.style.color = "lightgreen";
                setTimeout(() => ruleModal.classList.add('hidden'), 1500);
            }
        } catch (e) {
            ruleStatus.innerHTML = "❌ Failed to save rule.";
            ruleStatus.classList.remove('hidden');
            ruleStatus.style.color = "red";
        }
        submitRuleBtn.innerText = "Save to Rulebook";
    });

    // File Drag/Drop
    function handleFileSelection(file) {
        if (file) {
            selectionStatus.innerHTML = `📄 File Ready: <b>${file.name}</b>`;
            selectionStatus.classList.remove('hidden');
            dropZone.querySelector('p').innerHTML = `Selected: <b>${file.name}</b>`;
            dropZone.style.borderColor = '#06b6d4';
        }
    }

    dropZone.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', () => handleFileSelection(fileInput.files[0]));
    dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.style.borderColor = '#06b6d4'; });
    dropZone.addEventListener('dragleave', () => dropZone.style.borderColor = 'rgba(255,255,255,0.1)');
    dropZone.addEventListener('drop', (e) => { e.preventDefault(); fileInput.files = e.dataTransfer.files; handleFileSelection(fileInput.files[0]); });

    // Extraction Flow
    analyzeBtn.addEventListener('click', async () => {
        const formData = new FormData();
        if (fileInput.files[0]) formData.append('file', fileInput.files[0]);
        if (textInput.value) formData.append('text', textInput.value);
        if (customApiKeyInput.value) formData.append('api_key', customApiKeyInput.value);

        if (!fileInput.files[0] && !textInput.value) {
            alert('Please provide a file or text inquiry.');
            return;
        }

        uploadSection.classList.add('hidden');
        processingSection.classList.remove('hidden');
        progressBar.style.width = '50%';

        try {
            const response = await fetch('/analyze', { method: 'POST', body: formData });
            const result = await response.json();
            
            if (result.error) throw new Error(result.error);

            progressBar.style.width = '100%';
            
            // Add to sidebar history
            const projName = result.data.proposal_id || (fileInput.files[0] ? fileInput.files[0].name : 'Text Inquiry');
            addToHistory(projName);

            setTimeout(() => {
                displayResults(result.id, result.data);
            }, 800);

        } catch (error) {
            console.error(error);
            alert('Analysis failed. Check your API key or connection. ' + error.message);
            uploadSection.classList.remove('hidden');
            processingSection.classList.add('hidden');
        }
    });

    function addToHistory(name) {
        const emptyState = projectList.querySelector('.empty');
        if(emptyState) emptyState.remove();
        
        const item = document.createElement('div');
        item.className = 'project-item active';
        item.innerText = name;
        
        // Remove active from others
        projectList.querySelectorAll('.project-item').forEach(i => i.classList.remove('active'));
        projectList.prepend(item);
    }

    function displayResults(id, data) {
        currentInquiryId = id;
        currentData = data;
        
        processingSection.classList.add('hidden');
        downloadArea.classList.add('hidden');
        resultSection.classList.remove('hidden');
        
        renderDataForm(data);
    }

    // Dynamic rendering of nested JSON object
    function renderDataForm(data) {
        dataDisplay.innerHTML = '';

        Object.keys(data).forEach(key => {
            const val = data[key];
            if (val !== null && typeof val === 'object' && !Array.isArray(val)) {
                // Section (e.g. dimensions, loads)
                const sectionDiv = document.createElement('div');
                sectionDiv.className = 'form-section';
                sectionDiv.innerHTML = `<h3>${formatLabel(key)}</h3>`;
                
                const gridDiv = document.createElement('div');
                gridDiv.className = 'section-grid';
                
                Object.keys(val).forEach(subKey => {
                    gridDiv.appendChild(createInputCard(key, subKey, val[subKey]));
                });
                
                sectionDiv.appendChild(gridDiv);
                dataDisplay.appendChild(sectionDiv);
            } else {
                // Top level field (e.g. proposal_id)
                if(!dataDisplay.querySelector('.top-level-grid')) {
                    const topGrid = document.createElement('div');
                    topGrid.className = 'section-grid top-level-grid';
                    dataDisplay.appendChild(topGrid);
                }
                dataDisplay.querySelector('.top-level-grid').appendChild(createInputCard(null, key, val));
            }
        });
    }

    function createInputCard(parentKey, key, value) {
        const wrapper = document.createElement('div');
        wrapper.className = 'input-group';
        
        const labelText = formatLabel(key);
        const dataPath = parentKey ? `${parentKey}.${key}` : key;
        
        wrapper.innerHTML = `
            <label>${labelText}</label>
            <input type="${typeof value === 'number' ? 'number' : 'text'}" 
                   class="dynamic-input" 
                   data-path="${dataPath}" 
                   value="${value !== null ? value : ''}">
        `;
        return wrapper;
    }

    function formatLabel(str) {
        return str.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }

    // Dynamic Saving
    generateBtn.addEventListener('click', async () => {
        generateBtn.innerText = "Generating...";
        
        // Update currentData from inputs using data-path
        const inputs = document.querySelectorAll('.dynamic-input');
        inputs.forEach(input => {
            const path = input.getAttribute('data-path').split('.');
            let val = input.value;
            // Parse numbers if needed
            if (input.type === 'number' && val !== '') val = parseFloat(val);

            if (path.length === 1) {
                currentData[path[0]] = val;
            } else {
                currentData[path[0]][path[1]] = val;
            }
        });

        // Send modified data to backend
        const response = await fetch(`/generate/${currentInquiryId}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(currentData)
        });
        
        const result = await response.json();
        
        // Convert base64 to blob and auto-download
        const binaryString = window.atob(result.file_data_base64);
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }
        const blob = new Blob([bytes], {type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"});
        const url = URL.createObjectURL(blob);
        
        downloadArea.classList.remove('hidden');
        const a = document.createElement('a');
        a.href = url;
        a.download = result.filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        
        generateBtn.innerText = "Approve & Download Excel";
    });
});
