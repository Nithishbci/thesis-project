// Image Embed Form Handler
document.getElementById('imageEmbedForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    await processForm(this, '/embed_image', 'imageResults');
});

// Image Extract Form Handler
document.getElementById('imageExtractForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    await processForm(this, '/extract_image', 'imageResults');
});

// Audio Embed Form Handler
document.getElementById('audioEmbedForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    await processForm(this, '/embed_audio', 'audioResults');
});

// Audio Extract Form Handler
document.getElementById('audioExtractForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    await processForm(this, '/extract_audio', 'audioResults');
});

// Copy to clipboard function
function copyToClipboard(text, button) {
    navigator.clipboard.writeText(text).then(() => {
        // Show success feedback
        const originalHTML = button.innerHTML;
        button.innerHTML = '<i class="fas fa-check"></i> Copied!';
        button.classList.remove('btn-outline-secondary');
        button.classList.add('btn-success');
        
        setTimeout(() => {
            button.innerHTML = originalHTML;
            button.classList.remove('btn-success');
            button.classList.add('btn-outline-secondary');
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy: ', err);
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        
        const originalHTML = button.innerHTML;
        button.innerHTML = '<i class="fas fa-check"></i> Copied!';
        button.classList.remove('btn-outline-secondary');
        button.classList.add('btn-success');
        
        setTimeout(() => {
            button.innerHTML = originalHTML;
            button.classList.remove('btn-success');
            button.classList.add('btn-outline-secondary');
        }, 2000);
    });
}

async function processForm(form, url, resultsDiv) {
    const formData = new FormData(form);
    const resultsContainer = document.getElementById(resultsDiv);
    
    // Show loading
    resultsContainer.innerHTML = `
        <div class="loading-spinner">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-2">Processing...</p>
        </div>
    `;

    try {
        const response = await fetch(url, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            displayResults(data, resultsContainer, url.includes('embed'));
        } else {
            showError(data.error, resultsContainer);
        }
    } catch (error) {
        showError('Network error: ' + error.message, resultsContainer);
    }
}

function displayResults(data, container, isEmbed) {
    if (isEmbed) {
        container.innerHTML = createEmbedResultsHTML(data);
        // Add event listeners for copy buttons
        setTimeout(() => {
            addCopyButtonListeners();
        }, 100);
    } else {
        container.innerHTML = createExtractResultsHTML(data);
    }
}

function addCopyButtonListeners() {
    // Add click events to all copy buttons
    document.querySelectorAll('.copy-btn').forEach(button => {
        button.addEventListener('click', function() {
            const targetId = this.getAttribute('data-target');
            const textToCopy = document.getElementById(targetId).textContent;
            copyToClipboard(textToCopy, this);
        });
    });
}

function createEmbedResultsHTML(data) {
    return `
        <div class="alert alert-success alert-custom">
            <h6><i class="fas fa-check-circle"></i> Message Embedded Successfully!</h6>
        </div>

        ${data.stego_image ? `
        <div class="mb-3">
            <h6><i class="fas fa-image"></i> Stego Image</h6>
            <img src="data:image/png;base64,${data.stego_image}" class="stego-image img-fluid">
            <div class="mt-2">
                <small class="text-muted">Right-click and "Save image as" to download</small>
            </div>
        </div>
        ` : ''}

        ${data.stego_audio ? `
        <div class="mb-3">
            <h6><i class="fas fa-music"></i> Stego Audio</h6>
            <audio controls class="w-100">
                <source src="data:audio/wav;base64,${data.stego_audio}" type="audio/wav">
                Your browser does not support the audio element.
            </audio>
            <div class="mt-2">
                <small class="text-muted">Right-click and "Save audio as" to download</small>
            </div>
        </div>
        ` : ''}

        <div class="mb-3">
            <h6><i class="fas fa-key"></i> Cryptographic Keys</h6>
            <div class="row">
                <div class="col-md-6">
                    <div class="d-flex justify-content-between align-items-center mb-1">
                        <small class="text-muted">Private Key:</small>
                        <button class="btn btn-sm btn-outline-secondary copy-btn" data-target="private-key-text">
                            <i class="fas fa-copy"></i> Copy
                        </button>
                    </div>
                    <div id="private-key-text" class="ciphertext-display">${data.private_key}</div>
                </div>
                <div class="col-md-6">
                    <div class="d-flex justify-content-between align-items-center mb-1">
                        <small class="text-muted">Public Key:</small>
                        <button class="btn btn-sm btn-outline-secondary copy-btn" data-target="public-key-text">
                            <i class="fas fa-copy"></i> Copy
                        </button>
                    </div>
                    <div id="public-key-text" class="ciphertext-display">${data.public_key}</div>
                </div>
            </div>
            <div class="row mt-2">
                <div class="col-12">
                    <div class="d-flex justify-content-between align-items-center mb-1">
                        <small class="text-muted">AES Key:</small>
                        <button class="btn btn-sm btn-outline-secondary copy-btn" data-target="aes-key-text">
                            <i class="fas fa-copy"></i> Copy
                        </button>
                    </div>
                    <div id="aes-key-text" class="ciphertext-display">${data.aes_key}</div>
                </div>
            </div>
        </div>

        ${data.ciphertext_analysis ? `
        <div class="mb-3">
            <h6><i class="fas fa-lock"></i> Ciphertext Analysis</h6>
            <div class="row">
                <div class="col-md-6">
                    <small class="text-muted">Ciphertext Length:</small>
                    <div class="fw-bold">${data.ciphertext_analysis.ciphertext_length} bytes</div>
                </div>
                <div class="col-md-6">
                    <small class="text-muted">Entropy:</small>
                    <div class="fw-bold">${data.ciphertext_analysis.entropy.toFixed(4)}</div>
                </div>
            </div>
            
            <div class="mt-2">
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <small class="text-muted">Full Ciphertext (Hex):</small>
                    <button class="btn btn-sm btn-outline-secondary copy-btn" data-target="ciphertext-hex">
                        <i class="fas fa-copy"></i> Copy Full
                    </button>
                </div>
                <div id="ciphertext-hex" class="ciphertext-display">${data.ciphertext_analysis.ciphertext_hex}</div>
            </div>

            <div class="mt-2">
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <small class="text-muted">Ciphertext (Base64):</small>
                    <button class="btn btn-sm btn-outline-secondary copy-btn" data-target="ciphertext-base64">
                        <i class="fas fa-copy"></i> Copy
                    </button>
                </div>
                <div id="ciphertext-base64" class="ciphertext-display">${data.ciphertext_analysis.ciphertext_base64}</div>
            </div>

            <div class="mt-2">
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <small class="text-muted">Authentication Tag (Hex):</small>
                    <button class="btn btn-sm btn-outline-secondary copy-btn" data-target="tag-hex">
                        <i class="fas fa-copy"></i> Copy
                    </button>
                </div>
                <div id="tag-hex" class="ciphertext-display">${data.ciphertext_analysis.tag_hex}</div>
            </div>
        </div>
        ` : ''}

        <div class="mb-3">
            <h6><i class="fas fa-chart-bar"></i> Performance Metrics</h6>
            <div class="row">
                <div class="col-md-6">
                    <div class="metric-card">
                        <div class="metric-value">${data.metrics.embed_time.toFixed(2)}</div>
                        <div class="metric-label">Embed Time (ms)</div>
                    </div>
                </div>
                ${data.metrics.psnr ? `
                <div class="col-md-6">
                    <div class="metric-card">
                        <div class="metric-value">${data.metrics.psnr.toFixed(2)}</div>
                        <div class="metric-label">PSNR (dB)</div>
                    </div>
                </div>
                ` : ''}
                ${data.metrics.snr ? `
                <div class="col-md-6">
                    <div class="metric-card">
                        <div class="metric-value">${data.metrics.snr.toFixed(2)}</div>
                        <div class="metric-label">SNR (dB)</div>
                    </div>
                </div>
                ` : ''}
                <div class="col-md-6">
                    <div class="metric-card">
                        <div class="metric-value">${data.metrics.capacity_bits}</div>
                        <div class="metric-label">Capacity (bits)</div>
                    </div>
                </div>
                ${data.metrics.capacity_per_pixel ? `
                <div class="col-md-6">
                    <div class="metric-card">
                        <div class="metric-value">${data.metrics.capacity_per_pixel.toFixed(4)}</div>
                        <div class="metric-label">Bits/Pixel</div>
                    </div>
                </div>
                ` : ''}
                ${data.metrics.capacity_per_sample ? `
                <div class="col-md-6">
                    <div class="metric-card">
                        <div class="metric-value">${data.metrics.capacity_per_sample.toFixed(4)}</div>
                        <div class="metric-label">Bits/Sample</div>
                    </div>
                </div>
                ` : ''}
                <div class="col-md-6">
                    <div class="metric-card">
                        <div class="metric-value">${data.metrics.cpu_usage.toFixed(1)}%</div>
                        <div class="metric-label">CPU Usage</div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="metric-card">
                        <div class="metric-value">${data.metrics.memory_usage.toFixed(1)}</div>
                        <div class="metric-label">Memory (MB)</div>
                    </div>
                </div>
            </div>
        </div>

        <div class="alert alert-info">
            <small><i class="fas fa-info-circle"></i> Save the cryptographic keys securely for extraction!</small>
        </div>
    `;
}

function createExtractResultsHTML(data) {
    return `
        <div class="alert alert-success alert-custom">
            <h6><i class="fas fa-check-circle"></i> Message Extracted Successfully!</h6>
        </div>

        <div class="mb-3">
            <h6><i class="fas fa-envelope-open-text"></i> Decrypted Message</h6>
            <div class="alert alert-light border">
                <strong>${data.decrypted_message}</strong>
            </div>
        </div>

        <div class="mb-3">
            <h6><i class="fas fa-chart-bar"></i> Performance Metrics</h6>
            <div class="row">
                <div class="col-md-6">
                    <div class="metric-card">
                        <div class="metric-value">${data.metrics.extract_time.toFixed(2)}</div>
                        <div class="metric-label">Extract Time (ms)</div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="metric-card">
                        <div class="metric-value">${data.metrics.cpu_usage.toFixed(1)}%</div>
                        <div class="metric-label">CPU Usage</div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="metric-card">
                        <div class="metric-value">${data.metrics.memory_usage.toFixed(1)}</div>
                        <div class="metric-label">Memory (MB)</div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

function showError(message, container) {
    container.innerHTML = `
        <div class="alert alert-danger alert-custom">
            <h6><i class="fas fa-exclamation-triangle"></i> Error</h6>
            <p class="mb-0">${message}</p>
        </div>
    `;
}

// ... (previous code remains the same until the createEmbedResultsHTML function)

function createEmbedResultsHTML(data) {
    return `
        <div class="alert alert-success alert-custom">
            <h6><i class="fas fa-check-circle"></i> Message Embedded Successfully!</h6>
        </div>

        ${data.stego_image ? `
        <div class="mb-3">
            <h6><i class="fas fa-image"></i> Stego Image</h6>
            <img src="data:image/png;base64,${data.stego_image}" class="stego-image img-fluid">
            <div class="mt-2">
                <small class="text-muted">Right-click and "Save image as" to download</small>
            </div>
        </div>
        ` : ''}

        ${data.stego_audio ? `
        <div class="mb-3">
            <h6><i class="fas fa-music"></i> Stego Audio</h6>
            <audio controls class="w-100">
                <source src="data:audio/wav;base64,${data.stego_audio}" type="audio/wav">
                Your browser does not support the audio element.
            </audio>
            <div class="mt-2">
                <small class="text-muted">Right-click and "Save audio as" to download</small>
            </div>
        </div>
        ` : ''}

        <div class="mb-3">
            <h6><i class="fas fa-key"></i> Cryptographic Keys</h6>
            <div class="row">
                <div class="col-md-6">
                    <div class="d-flex justify-content-between align-items-center mb-1">
                        <small class="text-muted">Private Key:</small>
                        <button class="btn btn-sm btn-outline-secondary copy-btn" data-target="private-key-text">
                            <i class="fas fa-copy"></i> Copy
                        </button>
                    </div>
                    <div id="private-key-text" class="ciphertext-display">${data.private_key}</div>
                </div>
                <div class="col-md-6">
                    <div class="d-flex justify-content-between align-items-center mb-1">
                        <small class="text-muted">Public Key:</small>
                        <button class="btn btn-sm btn-outline-secondary copy-btn" data-target="public-key-text">
                            <i class="fas fa-copy"></i> Copy
                        </button>
                    </div>
                    <div id="public-key-text" class="ciphertext-display">${data.public_key}</div>
                </div>
            </div>
            <div class="row mt-2">
                <div class="col-12">
                    <div class="d-flex justify-content-between align-items-center mb-1">
                        <small class="text-muted">AES Key:</small>
                        <button class="btn btn-sm btn-outline-secondary copy-btn" data-target="aes-key-text">
                            <i class="fas fa-copy"></i> Copy
                        </button>
                    </div>
                    <div id="aes-key-text" class="ciphertext-display">${data.aes_key}</div>
                </div>
            </div>
        </div>

        ${data.ciphertext_analysis ? `
        <div class="mb-3">
            <h6><i class="fas fa-lock"></i> Ciphertext Analysis</h6>
            <div class="row">
                <div class="col-md-6">
                    <small class="text-muted">Ciphertext Length:</small>
                    <div class="fw-bold">${data.ciphertext_analysis.ciphertext_length} bytes</div>
                </div>
                <div class="col-md-6">
                    <small class="text-muted">Entropy:</small>
                    <div class="fw-bold">${data.ciphertext_analysis.entropy.toFixed(4)}</div>
                </div>
            </div>
            
            <div class="mt-2">
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <small class="text-muted">Full Ciphertext (Hex):</small>
                    <button class="btn btn-sm btn-outline-secondary copy-btn" data-target="ciphertext-hex">
                        <i class="fas fa-copy"></i> Copy Full
                    </button>
                </div>
                <div id="ciphertext-hex" class="ciphertext-display">${data.ciphertext_analysis.ciphertext_hex}</div>
            </div>

            <div class="mt-2">
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <small class="text-muted">Ciphertext (Base64):</small>
                    <button class="btn btn-sm btn-outline-secondary copy-btn" data-target="ciphertext-base64">
                        <i class="fas fa-copy"></i> Copy
                    </button>
                </div>
                <div id="ciphertext-base64" class="ciphertext-display">${data.ciphertext_analysis.ciphertext_base64}</div>
            </div>

            <div class="mt-2">
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <small class="text-muted">Authentication Tag (Hex):</small>
                    <button class="btn btn-sm btn-outline-secondary copy-btn" data-target="tag-hex">
                        <i class="fas fa-copy"></i> Copy
                    </button>
                </div>
                <div id="tag-hex" class="ciphertext-display">${data.ciphertext_analysis.tag_hex}</div>
            </div>
        </div>
        ` : ''}

        <div class="mb-3">
            <h6><i class="fas fa-chart-bar"></i> Performance Metrics</h6>
            <div class="row">
                <!-- Timing Metrics -->
                <div class="col-md-12 mb-2">
                    <h6 class="text-primary"><i class="fas fa-clock"></i> Timing Metrics (ms)</h6>
                </div>
                <div class="col-md-4">
                    <div class="metric-card">
                        <div class="metric-value">${data.metrics.encryption_time.toFixed(2)}</div>
                        <div class="metric-label">AES Encryption</div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="metric-card">
                        <div class="metric-value">${data.metrics.embed_time.toFixed(2)}</div>
                        <div class="metric-label">Stego Embedding</div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="metric-card">
                        <div class="metric-value">${data.metrics.total_time.toFixed(2)}</div>
                        <div class="metric-label">Total Time</div>
                    </div>
                </div>

                <!-- Quality Metrics -->
                <div class="col-md-12 mb-2 mt-2">
                    <h6 class="text-primary"><i class="fas fa-chart-line"></i> Quality Metrics</h6>
                </div>
                ${data.metrics.psnr ? `
                <div class="col-md-6">
                    <div class="metric-card">
                        <div class="metric-value">${data.metrics.psnr.toFixed(2)}</div>
                        <div class="metric-label">PSNR (dB)</div>
                    </div>
                </div>
                ` : ''}
                ${data.metrics.snr ? `
                <div class="col-md-6">
                    <div class="metric-card">
                        <div class="metric-value">${data.metrics.snr.toFixed(2)}</div>
                        <div class="metric-label">SNR (dB)</div>
                    </div>
                </div>
                ` : ''}

                <!-- Capacity Metrics -->
                <div class="col-md-12 mb-2 mt-2">
                    <h6 class="text-primary"><i class="fas fa-database"></i> Capacity Metrics</h6>
                </div>
                <div class="col-md-4">
                    <div class="metric-card">
                        <div class="metric-value">${data.metrics.capacity_bits}</div>
                        <div class="metric-label">Total Bits</div>
                    </div>
                </div>
                ${data.metrics.capacity_per_pixel ? `
                <div class="col-md-4">
                    <div class="metric-card">
                        <div class="metric-value">${data.metrics.capacity_per_pixel.toFixed(4)}</div>
                        <div class="metric-label">Bits/Pixel</div>
                    </div>
                </div>
                ` : ''}
                ${data.metrics.capacity_per_sample ? `
                <div class="col-md-4">
                    <div class="metric-card">
                        <div class="metric-value">${data.metrics.capacity_per_sample.toFixed(4)}</div>
                        <div class="metric-label">Bits/Sample</div>
                    </div>
                </div>
                ` : ''}

                <!-- Size Metrics -->
                <div class="col-md-12 mb-2 mt-2">
                    <h6 class="text-primary"><i class="fas fa-weight-hanging"></i> Size Metrics</h6>
                </div>
                <div class="col-md-6">
                    <div class="metric-card">
                        <div class="metric-value">${data.metrics.original_message_size}</div>
                        <div class="metric-label">Original (bytes)</div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="metric-card">
                        <div class="metric-value">${data.metrics.encrypted_data_size}</div>
                        <div class="metric-label">Encrypted (bytes)</div>
                    </div>
                </div>

                <!-- System Metrics -->
                <div class="col-md-12 mb-2 mt-2">
                    <h6 class="text-primary"><i class="fas fa-desktop"></i> System Metrics</h6>
                </div>
                <div class="col-md-6">
                    <div class="metric-card">
                        <div class="metric-value">${data.metrics.cpu_usage.toFixed(1)}%</div>
                        <div class="metric-label">CPU Usage</div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="metric-card">
                        <div class="metric-value">${data.metrics.memory_usage.toFixed(1)}</div>
                        <div class="metric-label">Memory (MB)</div>
                    </div>
                </div>
            </div>
        </div>

        <div class="alert alert-info">
            <small><i class="fas fa-info-circle"></i> Save the cryptographic keys securely for extraction!</small>
        </div>
    `;
}

function createExtractResultsHTML(data) {
    return `
        <div class="alert alert-success alert-custom">
            <h6><i class="fas fa-check-circle"></i> Message Extracted Successfully!</h6>
        </div>

        <div class="mb-3">
            <h6><i class="fas fa-envelope-open-text"></i> Decrypted Message</h6>
            <div class="alert alert-light border">
                <strong>${data.decrypted_message}</strong>
            </div>
        </div>

        <div class="mb-3">
            <h6><i class="fas fa-chart-bar"></i> Performance Metrics</h6>
            <div class="row">
                <!-- Timing Metrics -->
                <div class="col-md-12 mb-2">
                    <h6 class="text-primary"><i class="fas fa-clock"></i> Timing Metrics (ms)</h6>
                </div>
                <div class="col-md-4">
                    <div class="metric-card">
                        <div class="metric-value">${data.metrics.extract_time.toFixed(2)}</div>
                        <div class="metric-label">Stego Extraction</div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="metric-card">
                        <div class="metric-value">${data.metrics.decryption_time.toFixed(2)}</div>
                        <div class="metric-label">AES Decryption</div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="metric-card">
                        <div class="metric-value">${data.metrics.total_time.toFixed(2)}</div>
                        <div class="metric-label">Total Time</div>
                    </div>
                </div>

                <!-- System Metrics -->
                <div class="col-md-12 mb-2 mt-2">
                    <h6 class="text-primary"><i class="fas fa-desktop"></i> System Metrics</h6>
                </div>
                <div class="col-md-6">
                    <div class="metric-card">
                        <div class="metric-value">${data.metrics.cpu_usage.toFixed(1)}%</div>
                        <div class="metric-label">CPU Usage</div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="metric-card">
                        <div class="metric-value">${data.metrics.memory_usage.toFixed(1)}</div>
                        <div class="metric-label">Memory (MB)</div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// ... (rest of the code remains the same)