import { useState } from 'react';
import { Upload, Image as ImageIcon, X } from 'lucide-react';

const ImageUploader = ({ onImagesSelect, selectedImages, onClearImage }) => {
  const [isDragOver, setIsDragOver] = useState(false);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFilesSelect(Array.from(files));
    }
  };

  const validateFile = (file) => {
    if (!file.type.startsWith('image/')) return 'Please upload an image file (JPG, PNG).';
    if (file.size > 20 * 1024 * 1024) return 'Each file must be less than 20MB.';
    return null;
  };

  const handleFilesSelect = async (files) => {
    const valid = [];
    for (const file of files) {
      const err = validateFile(file);
      if (err) {
        alert(err);
        continue;
      }
      valid.push(file);
    }
    if (!valid.length) return;

    const readOne = (file) =>
      new Promise((resolve) => {
        const reader = new FileReader();
        reader.onload = (e) =>
          resolve({ file, url: e.target.result, name: file.name });
        reader.readAsDataURL(file);
      });

    const images = await Promise.all(valid.map(readOne));
    onImagesSelect(images);
  };

  const handleInputChange = (e) => {
    const files = Array.from(e.target.files ?? []);
    if (files.length) handleFilesSelect(files);
  };

  if (selectedImages && selectedImages.length > 0) {
    const primary = selectedImages[0];
    return (
      <div className="card card-hover">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="section-title">Scan uploaded</h3>
            <p className="section-subtitle">
              {selectedImages.length} image(s) ready for analysis
            </p>
          </div>
          <button
            onClick={onClearImage}
            className="btn-secondary px-3 py-2"
            type="button"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>
        
        <div className="flex items-center gap-4">
          <div className="w-24 h-24 bg-slate-100 rounded-xl overflow-hidden flex-shrink-0 border border-slate-200/70">
            <img 
              src={primary.url} 
              alt={primary.name}
              className="w-full h-full object-cover"
            />
          </div>
          <div>
            <p className="font-medium text-slate-900">{primary.name}</p>
            <p className="text-sm text-slate-500">
              {(primary.file.size / 1024 / 1024).toFixed(2)} MB
            </p>
          </div>
        </div>

        {selectedImages.length > 1 && (
          <div className="mt-4 flex gap-2 overflow-x-auto pb-1">
            {selectedImages.map((img, idx) => (
              <div
                key={`${img.name}-${idx}`}
                className="shrink-0 overflow-hidden rounded-xl border border-slate-200 bg-slate-100"
                title={img.name}
              >
                <img src={img.url} alt={img.name} className="h-14 w-20 object-cover" />
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="card card-hover">
      <div className="flex items-baseline justify-between gap-3 mb-4">
        <h3 className="section-title">Upload scan</h3>
        <span className="section-subtitle">JPG/PNG up to 20MB</span>
      </div>
      
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`border border-dashed rounded-2xl p-10 sm:p-12 text-center transition-all cursor-pointer ${
          isDragOver 
            ? 'border-blue-300 bg-blue-50/40' 
            : 'border-slate-300/80 hover:border-blue-300 hover:bg-blue-50/20'
        }`}
      >
        <input
          type="file"
          accept="image/*"
          multiple
          onChange={handleInputChange}
          className="hidden"
          id="image-upload"
        />
        <label htmlFor="image-upload" className="cursor-pointer">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-600/10 border border-blue-200/50">
            <Upload className="w-6 h-6 text-blue-700" />
          </div>
          <p className="text-lg font-semibold text-slate-900 mb-2">
            Drop X-ray image here or click to browse
          </p>
          <p className="text-sm text-slate-500">
            Accepts multiple JPG/PNG files up to 20MB each
          </p>
        </label>
      </div>
    </div>
  );
};

export default ImageUploader;
