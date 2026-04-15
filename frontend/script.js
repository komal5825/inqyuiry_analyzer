document.addEventListener('DOMContentLoaded', () => {
    const analyzeBtn = document.getElementById('analyze-btn');
    const uploadSection = document.getElementById('upload-section');
    const processingSection = document.getElementById('processing-section');
    const resultSection = document.getElementById('result-section');
    const dataDisplay = document.getElementById('data-display');
    const generateBtn = document.getElementById('generate-btn');
    const downloadArea = document.getElementById('download-area');
    const downloadLink = document.getElementById('download-link');
    const progressBar = document.getElementById('progress-bar');
    
    const fileInput = document.getElementById('file-input');
    const dropZone = document.getElementById('drop-zone');
    const textInput = document.getElementById('text-input');

    let currentInquiryId = null;
    let currentData = null;

    // UI Interaction
    const selectionStatus = document.getElementById('selection-status');

    function handleFileSelection(file) {
        if (file) {
            selectionStatus.innerHTML = `📄 File Ready: <b>${file.name}</b>`;
            selectionStatus.classList.remove('hidden');
            dropZone.querySelector('p').innerHTML = `Selected: <b>${file.name}</b>`;
            dropZone.style.borderColor = '#06b6d4';
        }
    }

    dropZone.addEventListener('click', () => fileInput.click());
    
    fileInput.addEventListener('change', () => {
        handleFileSelection(fileInput.files[0]);
    });

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = '#06b6d4';
    });
    dropZone.addEventListener('dragleave', () => dropZone.style.borderColor = 'rgba(255,255,255,0.1)');
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        fileInput.files = e.dataTransfer.files;
        handleFileSelection(fileInput.files[0]);
    });

    analyzeBtn.addEventListener('click', async () => {
        const formData = new FormData();
        if (fileInput.files[0]) formData.append('file', fileInput.files[0]);
        if (textInput.value) formData.append('text', textInput.value);

        if (!fileInput.files[0] && !textInput.value) {
            alert('Please provide a file or text inquiry.');
            return;
        }

        // Transition to Processing
        uploadSection.classList.add('hidden');
        processingSection.classList.remove('hidden');
        updateProgress(33, 'step-extracting');

        try {
            const response = await fetch('/analyze', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();
            
            // Show Upload Success Feedback
            const statusBadge = document.getElementById('upload-status');
            statusBadge.innerHTML = `✅ Successfully uploaded: <b>${result.upload_feedback.name}</b> (${result.upload_feedback.type})`;
            statusBadge.classList.remove('hidden');

            updateProgress(66, 'step-analyzing');
            
            // Artificial delay for premium feel
            setTimeout(() => {
                updateProgress(100, 'step-finalizing');
                setTimeout(() => {
                    displayResults(result.id, result.data);
                }, 800);
            }, 1000);

        } catch (error) {
            alert('Analysis failed. Please check your API connection.');
            uploadSection.classList.remove('hidden');
            processingSection.classList.add('hidden');
        }
    });

    function updateProgress(percent, stepId) {
        progressBar.style.width = percent + '%';
        document.querySelectorAll('.step').forEach(s => s.classList.remove('active'));
        document.getElementById(stepId).classList.add('active');
    }

    function displayResults(id, data) {
        currentInquiryId = id;
        currentData = data;
        
        processingSection.classList.add('hidden');
        resultSection.classList.remove('hidden');
        
        renderDataCards(data);
    }

    function renderDataCards(data) {
        dataDisplay.innerHTML = '';
        // Show key parameters
        // Show key parameters - Expanded for Deep Intent Analysis
        const keysToShow = [
            'proposal_id', 'date', 'length', 'width', 'height', 
            'location', 'project', 'mezzanine_height', 'crane_count', 
            'area', 'side_bay', 'end_bay'
        ];
        
        keysToShow.forEach(key => {
            const card = document.createElement('div');
            card.className = 'data-card';
            card.innerHTML = `
                <div class="label">${key.replace('_', ' ')}</div>
                <input type="text" class="value-input" data-key="${key}" value="${data[key]}">
            `;
            dataDisplay.appendChild(card);
        });
    }

    generateBtn.addEventListener('click', async () => {
        // Collect edited values
        const inputs = document.querySelectorAll('.value-input');
        inputs.forEach(input => {
            const key = input.getAttribute('data-key');
            currentData[key] = input.value;
        });

        const response = await fetch(`/generate/${currentInquiryId}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(currentData)
        });
        
        const result = await response.json();
        downloadLink.href = result.download_url;
        downloadArea.classList.remove('hidden');
        downloadArea.scrollIntoView({behavior: 'smooth'});
    });
});
