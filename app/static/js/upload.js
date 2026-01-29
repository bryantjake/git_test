/**
 * Upload page functionality
 */

document.addEventListener('DOMContentLoaded', () => {
    setupSingleUpload();
    setupBatchUpload();
});

// Setup single file upload
function setupSingleUpload() {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');

    // Click to browse
    dropZone.addEventListener('click', () => fileInput.click());

    // File input change
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            uploadSingleFile(e.target.files[0]);
        }
    });

    // Drag and drop
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('drag-over');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            uploadSingleFile(files[0]);
        }
    });
}

// Upload single file
async function uploadSingleFile(file) {
    if (!file.name.toLowerCase().endsWith('.fit')) {
        showNotification('Please select a .FIT file', 'error');
        return;
    }

    const progress = document.getElementById('upload-progress');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');

    progress.style.display = 'block';
    progressFill.style.width = '0%';
    progressText.textContent = 'Uploading...';

    try {
        // Simulate progress
        let progressValue = 0;
        const progressInterval = setInterval(() => {
            progressValue += 10;
            if (progressValue <= 90) {
                progressFill.style.width = progressValue + '%';
            }
        }, 100);

        const result = await API.uploadFile(file);

        clearInterval(progressInterval);
        progressFill.style.width = '100%';

        if (result.is_duplicate) {
            progressText.textContent = 'Activity already exists';
            showNotification('This activity has already been uploaded', 'error');
        } else {
            progressText.textContent = 'Upload successful!';
            showNotification('Activity uploaded successfully!', 'success');

            // Show new records if any
            if (result.new_records && result.new_records.length > 0) {
                const recordsMsg = result.new_records.map(r => r.record_name).join(', ');
                showNotification(`New personal records: ${recordsMsg}`, 'success');
            }

            // Show result with link
            showUploadResult([{
                filename: file.name,
                success: true,
                activity_id: result.activity.id,
                is_duplicate: false
            }]);
        }

    } catch (error) {
        progressFill.style.width = '100%';
        progressFill.style.backgroundColor = '#d63031';
        progressText.textContent = 'Upload failed: ' + error.message;
        showNotification('Upload failed: ' + error.message, 'error');
    }
}

// Setup batch upload
function setupBatchUpload() {
    const dropZone = document.getElementById('batch-drop-zone');
    const fileInput = document.getElementById('batch-file-input');

    // Click to browse
    dropZone.addEventListener('click', () => fileInput.click());

    // File input change
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            uploadBatchFiles(Array.from(e.target.files));
        }
    });

    // Drag and drop
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('drag-over');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');

        const files = Array.from(e.dataTransfer.files).filter(f =>
            f.name.toLowerCase().endsWith('.fit')
        );

        if (files.length > 0) {
            uploadBatchFiles(files);
        } else {
            showNotification('No .FIT files found', 'error');
        }
    });
}

// Upload batch files
async function uploadBatchFiles(files) {
    const fitFiles = files.filter(f => f.name.toLowerCase().endsWith('.fit'));

    if (fitFiles.length === 0) {
        showNotification('No .FIT files selected', 'error');
        return;
    }

    const progress = document.getElementById('batch-progress');
    const progressFill = document.getElementById('batch-progress-fill');
    const currentEl = document.getElementById('batch-current');
    const totalEl = document.getElementById('batch-total');

    progress.style.display = 'block';
    totalEl.textContent = fitFiles.length;
    currentEl.textContent = '0';
    progressFill.style.width = '0%';

    try {
        const result = await API.uploadBatch(fitFiles);

        currentEl.textContent = fitFiles.length;
        progressFill.style.width = '100%';

        // Show summary
        showNotification(
            `Uploaded ${result.successful} of ${result.total} files`,
            result.failed > 0 ? 'error' : 'success'
        );

        // Show detailed results
        showUploadResult(result.results);

    } catch (error) {
        showNotification('Batch upload failed: ' + error.message, 'error');
    }
}

// Show upload results
function showUploadResult(results) {
    const resultsSection = document.getElementById('upload-results');
    const resultsList = document.getElementById('results-list');
    const successCount = document.getElementById('success-count');
    const duplicateCount = document.getElementById('duplicate-count');
    const failedCount = document.getElementById('failed-count');

    resultsSection.style.display = 'block';

    const success = results.filter(r => r.success && !r.is_duplicate).length;
    const duplicates = results.filter(r => r.is_duplicate).length;
    const failed = results.filter(r => !r.success).length;

    successCount.textContent = success;
    duplicateCount.textContent = duplicates;
    failedCount.textContent = failed;

    resultsList.innerHTML = results.map(result => {
        let statusClass, statusText;

        if (result.success && !result.is_duplicate) {
            statusClass = 'success';
            statusText = 'Uploaded';
        } else if (result.is_duplicate) {
            statusClass = 'duplicate';
            statusText = 'Duplicate';
        } else {
            statusClass = 'error';
            statusText = result.error || 'Failed';
        }

        const link = result.activity_id
            ? `<a href="/activity/${result.activity_id}">View</a>`
            : '';

        return `
            <div class="result-item ${statusClass}">
                <span class="filename">${result.filename}</span>
                <span class="status">${statusText} ${link}</span>
            </div>
        `;
    }).join('');
}
