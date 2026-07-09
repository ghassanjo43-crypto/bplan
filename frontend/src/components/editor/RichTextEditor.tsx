import { useEffect, useRef, useState } from 'react'
import { EditorContent, useEditor, type Editor, type JSONContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Underline from '@tiptap/extension-underline'
import Link from '@tiptap/extension-link'
import Placeholder from '@tiptap/extension-placeholder'
import TextAlign from '@tiptap/extension-text-align'
import { BusinessPlanImage } from './extensions/BusinessPlanImage'
import { EditorToolbar } from './EditorToolbar'
import { imageSrc } from '@/api/textPlanApi'
import type { TextPlanImage } from '@/types/textPlan'

const EXTENSIONS = [
  StarterKit.configure({ heading: { levels: [2, 3] } }),
  Underline,
  Link.configure({ openOnClick: false, autolink: true }),
  BusinessPlanImage.configure({ inline: false, allowBase64: true }),
  TextAlign.configure({ types: ['heading', 'paragraph'] }),
]

export function RichTextEditor({
  content,
  editable = true,
  onChange,
  onReady,
  uploadImage,
  onUploadError,
  placeholder = 'Start writing this topic…',
}: {
  content: string | JSONContent
  editable?: boolean
  onChange?: (html: string, json: JSONContent, text: string) => void
  /** Exposes the underlying editor so callers can insert/replace content. */
  onReady?: (editor: Editor) => void
  uploadImage?: (file: File) => Promise<TextPlanImage>
  onUploadError?: (error: unknown) => void
  placeholder?: string
}) {
  const fileRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)

  const editor = useEditor({
    editable,
    extensions: editable ? [...EXTENSIONS, Placeholder.configure({ placeholder })] : EXTENSIONS,
    content: content || '',
    onUpdate: ({ editor }) => onChange?.(editor.getHTML(), editor.getJSON(), editor.getText()),
    editorProps: { attributes: { class: 'rte-content' } },
  })

  useEffect(() => {
    if (editor) onReady?.(editor)
  }, [editor, onReady])

  if (!editable) {
    return (
      <div className="rte rte--readonly business-plan-editor">
        <EditorContent editor={editor} className="rte-surface" />
      </div>
    )
  }

  const onPickFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file || !uploadImage || !editor) return
    setUploading(true)
    try {
      const img = await uploadImage(file)
      // custom attributes (imageId/caption/alignment/widthPercentage) come from
      // the BusinessPlanImage extension; cast since the base typing only knows src/alt/title.
      const setImage = editor.chain().focus().setImage as unknown as (attrs: Record<string, unknown>) => {
        run: () => boolean
      }
      setImage({
        src: imageSrc(img),
        alt: img.alt_text || '',
        title: img.caption || '',
        imageId: img.id,
        caption: img.caption || '',
        alignment: img.alignment || 'center',
        widthPercentage: img.display_width_percentage || 80,
      }).run()
    } catch (err) {
      onUploadError?.(err)
    } finally {
      setUploading(false)
    }
  }

  const words = editor ? editor.getText().trim().split(/\s+/).filter(Boolean).length : 0

  return (
    <div className="rte business-plan-editor">
      <EditorToolbar editor={editor} onInsertImage={uploadImage ? () => fileRef.current?.click() : undefined} />
      <EditorContent editor={editor} className="rte-surface" />
      <input ref={fileRef} type="file" accept="image/*" hidden onChange={onPickFile} />
      <div className="rte-footer">
        {uploading && <span style={{ color: '#2563eb', marginRight: 10 }}>Uploading image…</span>}
        <span>
          {words} word{words === 1 ? '' : 's'}
        </span>
      </div>
    </div>
  )
}
