// File management, AJAX upload with progress, and deletion modal
document.addEventListener('DOMContentLoaded', function () {
  const uploadForm = document.getElementById('fileUploadForm');
  const fileInput = document.getElementById('fileInput');
  const dropzone = document.getElementById('uploadDropzone');
  const selectedFileInfo = document.getElementById('selectedFileInfo');
  const selectedFileName = document.getElementById('selectedFileName');
  const selectedFileSize = document.getElementById('selectedFileSize');
  const uploadProgressBar = document.getElementById('uploadProgressBar');
  const uploadProgressContainer = document.getElementById('uploadProgressContainer');
  const uploadSubmitBtn = document.getElementById('uploadSubmitBtn');
  const uploadAlertBox = document.getElementById('uploadAlertBox');

  // Drag and drop handling
  if (dropzone && fileInput) {
    ['dragenter', 'dragover'].forEach(eventName => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.add('drag-over');
      }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.remove('drag-over');
      }, false);
    });

    dropzone.addEventListener('drop', (e) => {
      if (e.dataTransfer.files.length > 0) {
        fileInput.files = e.dataTransfer.files;
        handleFileSelect();
      }
    });

    dropzone.addEventListener('click', () => {
      fileInput.click();
    });

    fileInput.addEventListener('change', handleFileSelect);
  }

  function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  function handleFileSelect() {
    if (fileInput.files && fileInput.files[0]) {
      const file = fileInput.files[0];
      selectedFileName.textContent = file.name;
      selectedFileSize.textContent = formatBytes(file.size);
      selectedFileInfo.classList.remove('d-none');
      uploadSubmitBtn.disabled = false;
      uploadAlertBox.classList.add('d-none');
    }
  }

  // Upload with Progress Bar
  if (uploadForm) {
    uploadForm.addEventListener('submit', function (e) {
      e.preventDefault();
      if (!fileInput.files || !fileInput.files[0]) {
        showUploadAlert("Please choose a file to upload.", "warning");
        return;
      }

      const file = fileInput.files[0];
      const formData = new FormData(uploadForm);

      uploadSubmitBtn.disabled = true;
      uploadProgressContainer.classList.remove('d-none');
      uploadProgressBar.style.width = '0%';
      uploadProgressBar.textContent = '0%';
      uploadAlertBox.classList.add('d-none');

      const xhr = new XMLHttpRequest();
      xhr.open('POST', uploadForm.action, true);
      xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');

      xhr.upload.onprogress = function (e) {
        if (e.lengthComputable) {
          const percent = Math.round((e.loaded / e.total) * 100);
          uploadProgressBar.style.width = percent + '%';
          uploadProgressBar.textContent = percent + '%';
        }
      };

      xhr.onload = function () {
        uploadSubmitBtn.disabled = false;
        try {
          const res = JSON.parse(xhr.responseText);
          if (xhr.status >= 200 && xhr.status < 300 && res.success) {
            uploadProgressBar.classList.replace('bg-primary', 'bg-success');
            showUploadAlert(res.message, "success");
            setTimeout(() => {
              window.location.reload();
            }, 1200);
          } else {
            uploadProgressBar.classList.replace('bg-primary', 'bg-danger');
            showUploadAlert(res.message || "Upload failed.", res.quota_exceeded ? "danger" : "warning");
          }
        } catch (err) {
          showUploadAlert("Upload failed: Unexpected server response.", "danger");
        }
      };

      xhr.onerror = function () {
        uploadSubmitBtn.disabled = false;
        uploadProgressBar.classList.replace('bg-primary', 'bg-danger');
        showUploadAlert("Network or storage error occurred while uploading.", "danger");
      };

      xhr.send(formData);
    });
  }

  function showUploadAlert(msg, type) {
    if (uploadAlertBox) {
      uploadAlertBox.className = `alert alert-${type} mt-3 mb-0`;
      uploadAlertBox.textContent = msg;
      uploadAlertBox.classList.remove('d-none');
    }
  }

  // Delete Confirmation Modal Setup
  const deleteModal = document.getElementById('deleteConfirmModal');
  if (deleteModal) {
    deleteModal.addEventListener('show.bs.modal', function (event) {
      const button = event.relatedTarget;
      const fileId = button.getAttribute('data-file-id');
      const fileName = button.getAttribute('data-file-name');
      const deleteForm = document.getElementById('deleteFileForm');
      const deleteTargetName = document.getElementById('deleteTargetName');

      if (deleteTargetName) deleteTargetName.textContent = fileName;
      if (deleteForm) deleteForm.action = `/files/${fileId}/delete`;
    });
  }
});
