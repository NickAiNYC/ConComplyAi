import React, { useReducer, useRef } from 'react';

/**
 * DocumentUploadStation - File intake for contractor documents
 * 
 * RELIABILITY FIRST: Validate file types, sizes, quality before processing
 * Handles multi-page PDFs, photos, and scanned documents
 */

const uploadReducer = (state, action) => {
  switch (action.type) {
    case 'FILE_SELECTED':
      return { ...state, selectedFile: action.payload, uploadProgress: 0, uploadStatus: 'ready' };
    case 'UPLOAD_START':
      return { ...state, uploadStatus: 'uploading', uploadProgress: 0 };
    case 'UPLOAD_PROGRESS':
      return { ...state, uploadProgress: action.payload };
    case 'UPLOAD_COMPLETE':
      return { ...state, uploadStatus: 'complete', uploadProgress: 100, processedDoc: action.payload };
    case 'UPLOAD_ERROR':
      return { ...state, uploadStatus: 'error', errorMessage: action.payload };
    case 'DOC_TYPE_SELECT':
      return { ...state, documentType: action.payload };
    case 'RESET':
      return { selectedFile: null, uploadProgress: 0, uploadStatus: 'idle', documentType: 'COI', processedDoc: null, errorMessage: null };
    default:
      return state;
  }
};

const DocumentUploadStation = ({ onDocumentProcessed }) => {
  const [uploadState, dispatch] = useReducer(uploadReducer, {
    selectedFile: null,
    uploadProgress: 0,
    uploadStatus: 'idle',
    documentType: 'COI',
    processedDoc: null,
    errorMessage: null
  });

  const fileInputRef = useRef(null);

  const acceptedFileTypes = {
    'COI': ['.pdf', '.jpg', '.jpeg', '.png'],
    'LICENSE': ['.pdf', '.jpg', '.jpeg', '.png'],
    'OSHA_LOG': ['.pdf', '.xlsx', '.xls'],
    'LIEN_WAIVER': ['.pdf', '.jpg', '.jpeg', '.png']
  };

  const maxFileSizeMB = 10;

  const handleFileSelection = (event) => {
    const file = event.target.files[0];
    if (!file) return;

    // Validate file size
    if (file.size > maxFileSizeMB * 1024 * 1024) {
      dispatch({ type: 'UPLOAD_ERROR', payload: `File exceeds ${maxFileSizeMB}MB limit` });
      return;
    }

    // Validate file type
    const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
    const allowedTypes = acceptedFileTypes[uploadState.documentType];
    
    if (!allowedTypes.includes(fileExtension)) {
      dispatch({ type: 'UPLOAD_ERROR', payload: `Invalid file type. Expected: ${allowedTypes.join(', ')}` });
      return;
    }

    dispatch({ type: 'FILE_SELECTED', payload: file });
  };

  const simulateUploadProcessing = () => {
    dispatch({ type: 'UPLOAD_START' });

    // Simulate upload progress
    let progress = 0;
    const progressInterval = setInterval(() => {
      progress += 10;
      dispatch({ type: 'UPLOAD_PROGRESS', payload: progress });

      if (progress >= 100) {
        clearInterval(progressInterval);
        
        // Simulate document processing result
        setTimeout(() => {
          const mockProcessedDoc = {
            doc_identifier: `${uploadState.documentType}-${Date.now()}`,
            doc_category: uploadState.documentType,
            quality_metric: 0.87,
            skew_detected: false,
            crumple_detected: false,
            field_extractions: [
              {
                label: 'contractor_name',
                extracted_value: 'ABC Construction LLC',
                certainty: 0.95,
                bbox: { pg: 1, left: 0.1, top: 0.15, w: 0.3, h: 0.02 },
                method: 'OCR',
                contains_pii: false
              }
            ],
            compliance_status: true,
            compliance_issues: [],
            processing_cost_usd: 0.0052
          };

          dispatch({ type: 'UPLOAD_COMPLETE', payload: mockProcessedDoc });
          
          if (onDocumentProcessed) {
            onDocumentProcessed(mockProcessedDoc);
          }
        }, 500);
      }
    }, 200);
  };

  const triggerFileInput = () => {
    fileInputRef.current?.click();
  };

  const resetUpload = () => {
    dispatch({ type: 'RESET' });
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const docTypeOptions = [
    { value: 'COI', label: 'Certificate of Insurance', icon: '🛡️' },
    { value: 'LICENSE', label: 'Contractor License', icon: '📜' },
    { value: 'OSHA_LOG', label: 'OSHA 300 Log', icon: '📊' },
    { value: 'LIEN_WAIVER', label: 'Lien Waiver', icon: '📝' }
  ];

  return (
    <div style={styles.uploadStation}>
      <div style={styles.stationHeader}>
        <h2 style={styles.stationTitle}>Document Intake Station</h2>
        <p style={styles.stationSubtitle}>Upload contractor documentation for automated verification</p>
      </div>

      {/* Document Type Selector */}
      <div style={styles.typeSelector}>
        <label style={styles.selectorLabel}>Document Type:</label>
        <div style={styles.typeGrid}>
          {docTypeOptions.map(option => (
            <button
              key={option.value}
              style={{
                ...styles.typeButton,
                ...(uploadState.documentType === option.value ? styles.typeButtonActive : {})
              }}
              onClick={() => dispatch({ type: 'DOC_TYPE_SELECT', payload: option.value })}
              disabled={uploadState.uploadStatus === 'uploading'}
            >
              <span style={styles.typeIcon}>{option.icon}</span>
              <span style={styles.typeLabel}>{option.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Upload Area */}
      <div style={styles.uploadZone}>
        {uploadState.uploadStatus === 'idle' || uploadState.uploadStatus === 'ready' ? (
          <>
            <input
              ref={fileInputRef}
              type="file"
              accept={acceptedFileTypes[uploadState.documentType].join(',')}
              onChange={handleFileSelection}
              style={{ display: 'none' }}
            />
            <div 
              style={styles.dropZone}
              onClick={triggerFileInput}
            >
              {uploadState.selectedFile ? (
                <>
                  <div style={styles.filePreview}>
                    <span style={styles.fileIcon}>📄</span>
                    <div style={styles.fileInfo}>
                      <p style={styles.fileName}>{uploadState.selectedFile.name}</p>
                      <p style={styles.fileSize}>
                        {(uploadState.selectedFile.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                    </div>
                  </div>
                  <button 
                    style={styles.uploadButton}
                    onClick={(e) => {
                      e.stopPropagation();
                      simulateUploadProcessing();
                    }}
                  >
                    🚀 Process Document
                  </button>
                  <button 
                    style={styles.changeButton}
                    onClick={(e) => {
                      e.stopPropagation();
                      triggerFileInput();
                    }}
                  >
                    Change File
                  </button>
                </>
              ) : (
                <>
                  <span style={styles.uploadIcon}>⬆️</span>
                  <p style={styles.dropText}>Click to select or drag & drop</p>
                  <p style={styles.dropHint}>
                    Accepted: {acceptedFileTypes[uploadState.documentType].join(', ')} (max {maxFileSizeMB}MB)
                  </p>
                </>
              )}
            </div>
          </>
        ) : uploadState.uploadStatus === 'uploading' ? (
          <div style={styles.progressContainer}>
            <div style={styles.progressSpinner}>⏳</div>
            <p style={styles.progressText}>Processing document...</p>
            <div style={styles.progressBar}>
              <div 
                style={{
                  ...styles.progressFill,
                  width: `${uploadState.uploadProgress}%`
                }}
              />
            </div>
            <p style={styles.progressPercent}>{uploadState.uploadProgress}%</p>
          </div>
        ) : uploadState.uploadStatus === 'complete' ? (
          <div style={styles.successContainer}>
            <span style={styles.successIcon}>✅</span>
            <p style={styles.successText}>Document processed successfully!</p>
            <div style={styles.resultsSummary}>
              <p style={styles.resultItem}>
                <strong>Document ID:</strong> {uploadState.processedDoc.doc_identifier}
              </p>
              <p style={styles.resultItem}>
                <strong>Quality Score:</strong> {(uploadState.processedDoc.quality_metric * 100).toFixed(0)}%
              </p>
              <p style={styles.resultItem}>
                <strong>Fields Extracted:</strong> {uploadState.processedDoc.field_extractions.length}
              </p>
              <p style={styles.resultItem}>
                <strong>Status:</strong> {uploadState.processedDoc.compliance_status ? '✓ Compliant' : '✗ Non-Compliant'}
              </p>
            </div>
            <button style={styles.newUploadButton} onClick={resetUpload}>
              Upload Another Document
            </button>
          </div>
        ) : uploadState.uploadStatus === 'error' ? (
          <div style={styles.errorContainer}>
            <span style={styles.errorIcon}>❌</span>
            <p style={styles.errorText}>{uploadState.errorMessage}</p>
            <button style={styles.retryButton} onClick={resetUpload}>
              Try Again
            </button>
          </div>
        ) : null}
      </div>

      {/* Requirements Checklist */}
      <div style={styles.requirementsBox}>
        <h3 style={styles.requirementsTitle}>Document Requirements for {uploadState.documentType}</h3>
        <ul style={styles.requirementsList}>
          {uploadState.documentType === 'COI' && (
            <>
              <li style={styles.requirementItem}>✓ Certificate must be current (not expired)</li>
              <li style={styles.requirementItem}>✓ Additional Insured endorsement required</li>
              <li style={styles.requirementItem}>✓ Waiver of Subrogation must be indicated</li>
              <li style={styles.requirementItem}>✓ Minimum $2M per occurrence, $4M aggregate</li>
              <li style={styles.requirementItem}>✓ Certificate holder must match project owner</li>
            </>
          )}
          {uploadState.documentType === 'LICENSE' && (
            <>
              <li style={styles.requirementItem}>✓ License must be current (not expired)</li>
              <li style={styles.requirementItem}>✓ License type must match work scope</li>
              <li style={styles.requirementItem}>✓ Licensee name must match contractor</li>
            </>
          )}
          {uploadState.documentType === 'OSHA_LOG' && (
            <>
              <li style={styles.requirementItem}>✓ Log must cover current year</li>
              <li style={styles.requirementItem}>✓ All incidents must be documented</li>
              <li style={styles.requirementItem}>✓ Incident rate must be below industry average</li>
            </>
          )}
          {uploadState.documentType === 'LIEN_WAIVER' && (
            <>
              <li style={styles.requirementItem}>✓ Waiver must be properly executed (signed)</li>
              <li style={styles.requirementItem}>✓ Amount must match payment</li>
              <li style={styles.requirementItem}>✓ Through date must be specified</li>
            </>
          )}
        </ul>
      </div>

      {/* Quality Tips */}
      <div style={styles.tipsBox}>
        <h3 style={styles.tipsTitle}>📸 Quality Tips for Best Results</h3>
        <ul style={styles.tipsList}>
          <li style={styles.tipItem}>Use well-lit, high-resolution photos or scans</li>
          <li style={styles.tipItem}>Avoid skewed or tilted images - straighten before upload</li>
          <li style={styles.tipItem}>Flatten crumpled documents for clearer text</li>
          <li style={styles.tipItem}>Ensure all text is legible and in focus</li>
          <li style={styles.tipItem}>For multi-page docs, combine into single PDF</li>
        </ul>
      </div>
    </div>
  );
};

const styles = {
  uploadStation: {
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    maxWidth: '900px',
    margin: '0 auto',
    padding: '20px'
  },
  stationHeader: {
    textAlign: 'center',
    marginBottom: '30px'
  },
  stationTitle: {
    fontSize: '28px',
    fontWeight: '700',
    color: '#111827',
    marginBottom: '8px'
  },
  stationSubtitle: {
    fontSize: '16px',
    color: '#6b7280'
  },
  typeSelector: {
    marginBottom: '30px'
  },
  selectorLabel: {
    display: 'block',
    fontSize: '16px',
    fontWeight: '600',
    color: '#374151',
    marginBottom: '12px'
  },
  typeGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: '12px'
  },
  typeButton: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '8px',
    padding: '16px',
    backgroundColor: 'white',
    border: '2px solid #e5e7eb',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    fontSize: '14px'
  },
  typeButtonActive: {
    borderColor: '#3b82f6',
    backgroundColor: '#eff6ff'
  },
  typeIcon: {
    fontSize: '32px'
  },
  typeLabel: {
    fontWeight: '600',
    color: '#374151',
    textAlign: 'center'
  },
  uploadZone: {
    marginBottom: '30px'
  },
  dropZone: {
    border: '3px dashed #d1d5db',
    borderRadius: '12px',
    padding: '60px 40px',
    textAlign: 'center',
    backgroundColor: '#f9fafb',
    cursor: 'pointer',
    transition: 'all 0.2s ease'
  },
  uploadIcon: {
    fontSize: '64px',
    display: 'block',
    marginBottom: '16px'
  },
  dropText: {
    fontSize: '18px',
    fontWeight: '600',
    color: '#374151',
    marginBottom: '8px'
  },
  dropHint: {
    fontSize: '14px',
    color: '#6b7280'
  },
  filePreview: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '16px',
    marginBottom: '20px'
  },
  fileIcon: {
    fontSize: '48px'
  },
  fileInfo: {
    textAlign: 'left'
  },
  fileName: {
    fontSize: '16px',
    fontWeight: '600',
    color: '#111827',
    margin: '0 0 4px 0'
  },
  fileSize: {
    fontSize: '14px',
    color: '#6b7280',
    margin: '0'
  },
  uploadButton: {
    backgroundColor: '#10b981',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    padding: '12px 24px',
    fontSize: '16px',
    fontWeight: '600',
    cursor: 'pointer',
    marginRight: '12px'
  },
  changeButton: {
    backgroundColor: '#6b7280',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    padding: '12px 24px',
    fontSize: '16px',
    fontWeight: '600',
    cursor: 'pointer'
  },
  progressContainer: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '16px'
  },
  progressSpinner: {
    fontSize: '48px',
    animation: 'spin 2s linear infinite'
  },
  progressText: {
    fontSize: '18px',
    fontWeight: '600',
    color: '#374151'
  },
  progressBar: {
    width: '100%',
    height: '20px',
    backgroundColor: '#e5e7eb',
    borderRadius: '10px',
    overflow: 'hidden'
  },
  progressFill: {
    height: '100%',
    backgroundColor: '#3b82f6',
    transition: 'width 0.3s ease'
  },
  progressPercent: {
    fontSize: '24px',
    fontWeight: '700',
    color: '#3b82f6'
  },
  successContainer: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '16px'
  },
  successIcon: {
    fontSize: '64px'
  },
  successText: {
    fontSize: '20px',
    fontWeight: '600',
    color: '#10b981'
  },
  resultsSummary: {
    backgroundColor: '#f0fdf4',
    borderRadius: '8px',
    padding: '20px',
    width: '100%',
    textAlign: 'left'
  },
  resultItem: {
    fontSize: '14px',
    color: '#374151',
    margin: '8px 0'
  },
  newUploadButton: {
    backgroundColor: '#3b82f6',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    padding: '12px 24px',
    fontSize: '16px',
    fontWeight: '600',
    cursor: 'pointer'
  },
  errorContainer: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '16px'
  },
  errorIcon: {
    fontSize: '64px'
  },
  errorText: {
    fontSize: '18px',
    fontWeight: '600',
    color: '#ef4444'
  },
  retryButton: {
    backgroundColor: '#ef4444',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    padding: '12px 24px',
    fontSize: '16px',
    fontWeight: '600',
    cursor: 'pointer'
  },
  requirementsBox: {
    backgroundColor: '#eff6ff',
    borderRadius: '8px',
    padding: '20px',
    marginBottom: '20px'
  },
  requirementsTitle: {
    fontSize: '16px',
    fontWeight: '600',
    color: '#1e40af',
    marginBottom: '12px'
  },
  requirementsList: {
    margin: '0',
    paddingLeft: '20px'
  },
  requirementItem: {
    fontSize: '14px',
    color: '#1e3a8a',
    marginBottom: '8px'
  },
  tipsBox: {
    backgroundColor: '#f3f4f6',
    borderRadius: '8px',
    padding: '20px'
  },
  tipsTitle: {
    fontSize: '16px',
    fontWeight: '600',
    color: '#374151',
    marginBottom: '12px'
  },
  tipsList: {
    margin: '0',
    paddingLeft: '20px'
  },
  tipItem: {
    fontSize: '14px',
    color: '#6b7280',
    marginBottom: '8px'
  }
};

export default DocumentUploadStation;
