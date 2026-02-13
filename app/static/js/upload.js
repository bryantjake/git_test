document.addEventListener('DOMContentLoaded', () => {
    let uploadMap = null;
    let uploadMarker = null;
    let selectedFile = null;

    // Init map
    uploadMap = L.map('upload-map', {
        center: [39.8283, -98.5795],
        zoom: 4,
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
        maxZoom: 19,
    }).addTo(uploadMap);

    uploadMap.on('click', (e) => {
        const { lat, lng } = e.latlng;

        if (uploadMarker) {
            uploadMarker.setLatLng([lat, lng]);
        } else {
            uploadMarker = L.marker([lat, lng], {
                icon: L.divIcon({
                    className: 'upload-marker',
                    html: '<div style="width:20px;height:20px;background:#00e676;border:3px solid white;border-radius:50%;box-shadow:0 0 10px rgba(0,230,118,0.5);"></div>',
                    iconSize: [20, 20],
                    iconAnchor: [10, 10],
                }),
            }).addTo(uploadMap);
        }

        document.getElementById('latitude').value = lat;
        document.getElementById('longitude').value = lng;
        document.getElementById('coords-text').textContent =
            `${lat.toFixed(4)}, ${lng.toFixed(4)}`;

        checkFormValid();
    });

    // File handling
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const previewImg = document.getElementById('preview-img');
    const dropContent = document.getElementById('drop-zone-content');

    dropZone.addEventListener('click', (e) => {
        if (e.target.tagName !== 'LABEL' && e.target.tagName !== 'INPUT') {
            fileInput.click();
        }
    });

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
        if (e.dataTransfer.files.length > 0) {
            handleFile(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFile(e.target.files[0]);
        }
    });

    function handleFile(file) {
        if (!file.type.startsWith('image/')) {
            alert('Please select an image file.');
            return;
        }

        selectedFile = file;
        const reader = new FileReader();
        reader.onload = (e) => {
            previewImg.src = e.target.result;
            previewImg.style.display = 'block';
            dropContent.style.display = 'none';
        };
        reader.readAsDataURL(file);
        checkFormValid();
    }

    function checkFormValid() {
        const hasFile = selectedFile !== null;
        const hasYear = document.getElementById('year').value.trim() !== '';
        const hasLocation = document.getElementById('latitude').value !== '';
        document.getElementById('submit-btn').disabled = !(hasFile && hasYear && hasLocation);
    }

    document.getElementById('year').addEventListener('input', checkFormValid);

    // Submit form
    document.getElementById('upload-form').addEventListener('submit', async (e) => {
        e.preventDefault();

        const formData = new FormData();
        formData.append('file', selectedFile);
        formData.append('year', document.getElementById('year').value);
        formData.append('latitude', document.getElementById('latitude').value);
        formData.append('longitude', document.getElementById('longitude').value);
        formData.append('location_name', document.getElementById('location-name').value);
        formData.append('description', document.getElementById('description').value);

        const btn = document.getElementById('submit-btn');
        btn.disabled = true;
        btn.textContent = 'Uploading...';

        try {
            const res = await fetch('/api/photos', {
                method: 'POST',
                body: formData,
            });

            if (!res.ok) {
                const err = await res.json();
                alert(err.error || 'Upload failed');
                return;
            }

            // Reset form
            selectedFile = null;
            previewImg.style.display = 'none';
            dropContent.style.display = '';
            document.getElementById('upload-form').reset();
            document.getElementById('coords-text').textContent = 'No location selected';

            if (uploadMarker) {
                uploadMap.removeLayer(uploadMarker);
                uploadMarker = null;
            }

            loadPhotos();
        } catch (err) {
            alert('Upload failed. Please try again.');
        } finally {
            btn.textContent = 'Upload Photo';
            btn.disabled = true;
        }
    });

    // Load photos list
    async function loadPhotos() {
        try {
            const res = await fetch('/api/photos');
            const photos = await res.json();

            const list = document.getElementById('photos-list');
            document.getElementById('photo-count').textContent = `(${photos.length})`;

            if (photos.length === 0) {
                list.innerHTML = '<p class="empty-state">No photos uploaded yet.</p>';
                return;
            }

            list.innerHTML = photos.map(photo => `
                <div class="photo-item" data-id="${photo.id}">
                    <img src="/api/photos/file/${photo.filename}" alt="NFL Photo" />
                    <div class="photo-item-info">
                        <div class="photo-title">${photo.description || 'NFL Photo'}</div>
                        <div class="photo-meta">
                            Year: ${photo.year} | ${photo.location_name || `${photo.latitude.toFixed(2)}, ${photo.longitude.toFixed(2)}`}
                        </div>
                    </div>
                    <button class="btn-danger-sm" onclick="deletePhoto(${photo.id})">Delete</button>
                </div>
            `).join('');
        } catch (err) {
            console.error('Failed to load photos:', err);
        }
    }

    // Delete photo
    window.deletePhoto = async function(id) {
        if (!confirm('Delete this photo?')) return;

        try {
            await fetch(`/api/photos/${id}`, { method: 'DELETE' });
            loadPhotos();
        } catch (err) {
            alert('Failed to delete photo.');
        }
    };

    // Initial load
    loadPhotos();
});
