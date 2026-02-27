'use client';

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const API = process.env.NEXT_PUBLIC_API_BASE ?? '';

type DriveItem = {
  id: string;
  name: string;
  size?: number;
  lastModifiedDateTime: string;
  file?: { mimeType: string };
  folder?: { childCount: number };
  webUrl?: string;
};

function formatSize(bytes?: number) {
  if (!bytes) return '';
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)}KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function fileIcon(item: DriveItem) {
  if (item.folder) return '📁';
  const mime = item.file?.mimeType ?? '';
  if (mime.includes('pdf')) return '📄';
  if (mime.includes('word') || mime.includes('document')) return '📝';
  if (mime.includes('sheet') || mime.includes('excel')) return '📊';
  if (mime.includes('presentation') || mime.includes('powerpoint')) return '📑';
  if (mime.includes('image')) return '🖼';
  return '📎';
}

function isOfficeFile(item: DriveItem) {
  const mime = item.file?.mimeType ?? '';
  return (
    mime.includes('word') || mime.includes('document') ||
    mime.includes('sheet') || mime.includes('excel') ||
    mime.includes('presentation') || mime.includes('powerpoint')
  );
}

function isPdf(item: DriveItem) {
  return (item.file?.mimeType ?? '').includes('pdf');
}

function Panel({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={`bg-[#0f1720] border border-[rgba(255,255,255,0.08)] ${className ?? ''}`}
      style={{ clipPath: 'polygon(0 0,calc(100% - 10px) 0,100% 10px,100% 100%,0 100%)' }}
    >
      {children}
    </div>
  );
}

type Breadcrumb = { id: string | null; name: string };

export default function FounderFilesPage() {
  const [items, setItems] = useState<DriveItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [breadcrumbs, setBreadcrumbs] = useState<Breadcrumb[]>([{ id: null, name: 'OneDrive' }]);
  const [previewItem, setPreviewItem] = useState<DriveItem | null>(null);
  const [previewUrl, setPreviewUrl] = useState('');
  const [previewLoading, setPreviewLoading] = useState(false);

  const loadFolder = (itemId: string | null) => {
    setLoading(true);
    const url = itemId
      ? `${API}/api/v1/founder/graph/drive/folders/${itemId}`
      : `${API}/api/v1/founder/graph/drive`;
    fetch(url)
      .then((r) => r.json())
      .then((d) => setItems(d.value ?? []))
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadFolder(null); }, []);

  const navigate = (item: DriveItem) => {
    if (item.folder) {
      setBreadcrumbs((prev) => [...prev, { id: item.id, name: item.name }]);
      loadFolder(item.id);
    } else {
      openPreview(item);
    }
  };

  const navigateBreadcrumb = (crumb: Breadcrumb, idx: number) => {
    setBreadcrumbs((prev) => prev.slice(0, idx + 1));
    loadFolder(crumb.id);
  };

  const openPreview = async (item: DriveItem) => {
    setPreviewItem(item);
    setPreviewUrl('');
    setPreviewLoading(false);
    if (isOfficeFile(item) && item.webUrl) {
      setPreviewUrl(`https://view.officeapps.live.com/op/embed.aspx?src=${encodeURIComponent(item.webUrl)}`);
    } else if (isPdf(item)) {
      setPreviewLoading(true);
      fetch(`${API}/api/v1/founder/graph/drive/items/${item.id}/download-url`)
        .then((r) => r.json())
        .then((d) => setPreviewUrl(d.download_url ?? ''))
        .catch(() => setPreviewUrl(''))
        .finally(() => setPreviewLoading(false));
    }
  };

  const downloadItem = async (item: DriveItem) => {
    const resp = await fetch(`${API}/api/v1/founder/graph/drive/items/${item.id}/download-url`);
    const d = await resp.json();
    if (d.download_url) window.open(d.download_url, '_blank');
  };

  return (
    <div className="p-5 space-y-5 min-h-screen">
      <div>
        <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-[rgba(255,107,26,0.6)] mb-1">FOUNDER TOOLS · MICROSOFT GRAPH</div>
        <h1 className="text-xl font-black uppercase tracking-wider text-white">OneDrive Files</h1>
        <p className="text-[11px] text-[rgba(255,255,255,0.38)] mt-0.5">Application permissions · Founder drive only · All calls proxied through backend</p>
      </div>

      <div className="flex items-center gap-1 text-[11px] text-[rgba(255,255,255,0.4)]">
        {breadcrumbs.map((crumb, idx) => (
          <span key={idx} className="flex items-center gap-1">
            {idx > 0 && <span className="text-[rgba(255,255,255,0.2)]">/</span>}
            <button
              onClick={() => navigateBreadcrumb(crumb, idx)}
              className={`hover:text-white transition-colors ${idx === breadcrumbs.length - 1 ? 'text-white font-semibold' : ''}`}
            >
              {crumb.name}
            </button>
          </span>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        <Panel className="lg:col-span-2">
          <div className="p-3 border-b border-[rgba(255,255,255,0.06)] text-[10px] font-semibold uppercase tracking-widest text-[rgba(255,255,255,0.38)]">
            Files {!loading && `· ${items.length} items`}
          </div>
          {loading ? (
            <div className="p-6 text-center text-xs text-[rgba(255,255,255,0.3)]">Loading...</div>
          ) : items.length === 0 ? (
            <div className="p-6 text-center text-xs text-[rgba(255,255,255,0.3)]">Empty folder</div>
          ) : (
            <div className="divide-y divide-[rgba(255,255,255,0.04)] max-h-[65vh] overflow-y-auto">
              {items.map((item) => (
                <motion.button
                  key={item.id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  onClick={() => navigate(item)}
                  className={`w-full text-left px-3 py-3 hover:bg-[rgba(255,255,255,0.03)] transition-colors ${previewItem?.id === item.id ? 'bg-[rgba(255,107,26,0.06)] border-l-2 border-[#ff6b1a]' : ''}`}
                >
                  <div className="flex items-center gap-2">
                    <span className="text-base leading-none">{fileIcon(item)}</span>
                    <div className="flex-1 min-w-0">
                      <div className="text-[11px] text-[rgba(255,255,255,0.8)] truncate font-medium">{item.name}</div>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-[10px] text-[rgba(255,255,255,0.3)]">{formatDate(item.lastModifiedDateTime)}</span>
                        {item.size != null && <span className="text-[10px] text-[rgba(255,255,255,0.25)]">{formatSize(item.size)}</span>}
                        {item.folder && <span className="text-[10px] text-[rgba(255,255,255,0.25)]">{item.folder.childCount} items</span>}
                      </div>
                    </div>
                    {!item.folder && (
                      <button
                        onClick={(e) => { e.stopPropagation(); downloadItem(item); }}
                        className="text-[10px] text-[rgba(255,255,255,0.3)] hover:text-[#ff6b1a] transition-colors px-1"
                        title="Download"
                      >
                        ↓
                      </button>
                    )}
                  </div>
                </motion.button>
              ))}
            </div>
          )}
        </Panel>

        <Panel className="lg:col-span-3">
          <AnimatePresence mode="wait">
            {previewItem ? (
              <motion.div key={previewItem.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex flex-col h-full">
                <div className="p-3 border-b border-[rgba(255,255,255,0.06)] flex items-center justify-between">
                  <div>
                    <div className="text-[11px] font-semibold text-white truncate max-w-[300px]">{previewItem.name}</div>
                    <div className="text-[10px] text-[rgba(255,255,255,0.35)]">
                      {previewItem.file?.mimeType ?? ''} · {formatSize(previewItem.size)}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    {previewItem.webUrl && (
                      <a
                        href={previewItem.webUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="px-3 py-1.5 text-[10px] font-semibold uppercase border border-[rgba(255,255,255,0.1)] text-[rgba(255,255,255,0.5)] hover:text-white transition-colors"
                      >
                        Open
                      </a>
                    )}
                    <button
                      onClick={() => downloadItem(previewItem)}
                      className="px-3 py-1.5 text-[10px] font-semibold uppercase border border-[rgba(255,107,26,0.3)] text-[#ff6b1a] hover:bg-[rgba(255,107,26,0.1)] transition-colors"
                    >
                      Download
                    </button>
                    <button onClick={() => setPreviewItem(null)} className="text-[rgba(255,255,255,0.3)] hover:text-white px-2 transition-colors">
                      ✕
                    </button>
                  </div>
                </div>
                <div className="flex-1 p-4 overflow-hidden">
                  {previewLoading ? (
                    <div className="flex items-center justify-center h-40 text-xs text-[rgba(255,255,255,0.3)]">Loading preview...</div>
                  ) : previewUrl && (isOfficeFile(previewItem) || isPdf(previewItem)) ? (
                    <iframe
                      src={previewUrl}
                      className="w-full h-full min-h-[420px] border-0 rounded-sm"
                      title={previewItem.name}
                      allow="fullscreen"
                    />
                  ) : (
                    <div className="flex flex-col items-center justify-center h-40 gap-3">
                      <div className="text-4xl">{fileIcon(previewItem)}</div>
                      <div className="text-xs text-[rgba(255,255,255,0.5)]">{previewItem.name}</div>
                      <div className="text-[10px] text-[rgba(255,255,255,0.3)]">Preview not available for this file type</div>
                      {previewItem.webUrl && (
                        <a href={previewItem.webUrl} target="_blank" rel="noopener noreferrer" className="text-[11px] text-[#ff6b1a] hover:underline">
                          Open in browser
                        </a>
                      )}
                    </div>
                  )}
                </div>
              </motion.div>
            ) : (
              <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-center justify-center h-full p-12">
                <div className="text-center">
                  <div className="text-[rgba(255,255,255,0.15)] text-4xl mb-3">📁</div>
                  <div className="text-xs text-[rgba(255,255,255,0.3)]">Select a file to preview</div>
                  <div className="text-[10px] text-[rgba(255,255,255,0.2)] mt-1">Word, Excel, PowerPoint open in Office Online</div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </Panel>
      </div>
    </div>
  );
}
