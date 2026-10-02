import { useEffect, useState } from 'react'
import { api, ApiError } from '@/api/client'
import DeckPreview from '@/components/preview/DeckPreview'
import { Button, Field, Progress, Segmented, Select } from '@/components/ui'
import { Icon } from '@/lib/icons'
import type {
  Doc,
  FormatInfo,
  Job,
  OutputDetail,
  PresentationOutlineRequest,
  PresentationOutlineResponse,
  SlideOutlineItem,
  IRNode,
  ContentIR,
} from '@/types/api'

interface Props {
  format: FormatInfo
  sources: Doc[]
  languages: string[]
  initialSource?: string
  initialEditId?: string
  onCancel?: () => void
  onCreated: (outputIds: string[]) => void
}

const PURPOSES = [
  { key: 'executive briefing', label: 'Executive Briefing' },
  { key: 'technical briefing', label: 'Technical Briefing' },
  { key: 'research/findings', label: 'Research / Findings' },
  { key: 'public awareness', label: 'Public Awareness' },
  { key: 'project proposal', label: 'Project Proposal' },
  { key: 'training', label: 'Training' },
]

const AUDIENCES = [
  { key: 'technical', label: 'Technical Team' },
  { key: 'officials', label: 'Officials' },
  { key: 'public', label: 'Public' },
  { key: 'team', label: 'Team' },
  { key: 'researchers', label: 'Researchers / Experts' },
  { key: 'students', label: 'Students / Trainees' },
  { key: 'senior_leadership', label: 'Senior Leadership' },
]

const SLIDE_COUNTS = [
  { key: '5', label: '5 slides' },
  { key: '8', label: '8 slides' },
  { key: '10', label: '10 slides' },
  { key: '12', label: '12 slides' },
  { key: '15', label: '15 slides' },
  { key: '20', label: '20 slides' },
  { key: 'auto', label: 'Let AI decide' },
]

const DURATIONS = [
  { key: '5', label: '5 mins' },
  { key: '10', label: '10 mins' },
  { key: '15', label: '15 mins' },
  { key: '30', label: '30 mins' },
]

const THEMES = [
  { key: 'corporate_blue', label: 'Corporate Blue', swatch: 'bg-blue-700' },
  { key: 'midnight_dark', label: 'Midnight Dark', swatch: 'bg-slate-900' },
  { key: 'minimal_monochrome', label: 'Minimal Monochrome', swatch: 'bg-zinc-800' },
  { key: 'modern_gradient', label: 'Modern Gradient', swatch: 'bg-indigo-600' },
  { key: 'academic_research', label: 'Academic Research', swatch: 'bg-amber-900' },
  { key: 'data_analytics', label: 'Data & Analytics', swatch: 'bg-teal-600' },
  { key: 'warm_editorial', label: 'Warm Editorial', swatch: 'bg-orange-700' },
  { key: 'high_contrast', label: 'High-Contrast Presentation', swatch: 'bg-yellow-500' },
]

const LAYOUT_OPTIONS = [
  { key: 'standard_bullet', label: 'Standard Bullets' },
  { key: 'two_column', label: 'Two-Column Split' },
  { key: 'process', label: 'Process Flow' },
  { key: 'timeline', label: 'Timeline' },
  { key: 'metrics', label: 'Key Metrics' },
  { key: 'comparison', label: 'Comparison' },
  { key: 'table', label: 'Data Table' },
  { key: 'section_divider', label: 'Section Divider' },
  { key: 'image', label: 'Image with Caption' },
  { key: 'key_takeaways', label: 'Key Takeaways' },
  { key: 'references', label: 'References' },
]

export default function PPTStudio({
  format: _format,
  sources,
  languages,
  initialSource,
  initialEditId,
  onCreated,
  onCancel: _onCancel,
}: Props) {
  const readySources = sources.filter((d) => d.status === 'ready')
  const [step, setStep] = useState<1 | 2 | 3 | 4 | 5>(1)

  // Document Upload & Selection State
  const [selectedSourceId, setSelectedSourceId] = useState<string>(
    initialSource && readySources.some((d) => d.id === initialSource)
      ? initialSource
      : readySources[0]?.id ?? '',
  )
  const [uploading, setUploading] = useState(false)
  const [uploadDoc, setUploadDoc] = useState<Doc | null>(null)

  // Presentation Configuration State
  const [config, setConfig] = useState<PresentationOutlineRequest>({
    title: '',
    purpose: 'executive briefing',
    audience: 'officials',
    slide_count: 'auto',
    duration: '10',
    language: 'en',
    content_detail: 'balanced',
    theme: 'corporate_blue',
    visual_preference: 'balanced',
    speaker_notes: true,
    additional_instructions: '',
  })

  // Outline State
  const [generatingOutline, setGeneratingOutline] = useState(false)
  const [outline, setOutline] = useState<PresentationOutlineResponse | null>(null)

  // Full Deck Generation State
  const [job, setJob] = useState<Job | null>(null)
  const [generatingDeck, setGeneratingDeck] = useState(false)
  const [_createdOutputId, setCreatedOutputId] = useState<string | null>(null)
  const [outputDetail, setOutputDetail] = useState<OutputDetail | null>(null)

  // Slide Studio Editor State
  const [activeSlideIndex, setActiveSlideIndex] = useState(0)
  const [editingSlide, setEditingSlide] = useState<IRNode | null>(null)
  const [slideInstructions, setSlideInstructions] = useState('')
  const [regeneratingSlide, setRegeneratingSlide] = useState(false)
  const [_savingSlide, setSavingSlide] = useState(false)
  const [exporting, setExporting] = useState(false)

  // --- EDIT PRESENTATION WORKSPACE STATE ---
  const [isEditingWorkspace, setIsEditingWorkspace] = useState(false)
  const [editConfig, setEditConfig] = useState<PresentationOutlineRequest>({ ...config })
  const [changeSummary, setChangeSummary] = useState<string[]>([])
  const [showReconfigModal, setShowReconfigModal] = useState(false)
  const [reconfigScope, setReconfigScope] = useState<'all' | 'selected'>('all')
  const [selectedSlideIdsForRegen, setSelectedSlideIdsForRegen] = useState<string[]>([])
  const [preserveUserEdits, setPreserveUserEdits] = useState(true)
  const [proposedOutline, setProposedOutline] = useState<PresentationOutlineResponse | null>(null)
  const [adjustingCount, setAdjustingCount] = useState(false)
  const [reconfiguring, setReconfiguring] = useState(false)
  const [reverting, setReverting] = useState(false)

  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (readySources.length > 0 && !selectedSourceId) {
      setSelectedSourceId(readySources[0].id)
    }
  }, [readySources, selectedSourceId])

  useEffect(() => {
    if (initialEditId) {
      api
        .getOutput(initialEditId)
        .then((detail) => {
          setOutputDetail(detail)
          setCreatedOutputId(detail.id)
          if (detail.document_id) {
            setSelectedSourceId(detail.document_id)
          }
          const ctrls = (detail.controls || {}) as Record<string, any>
          const slidesCount = String(
            detail.content_ir.nodes.filter((n) => n.kind === 'slide').length + 1,
          )
          const loadedConfig: PresentationOutlineRequest = {
            title: detail.content_ir.title || '',
            purpose: ctrls.purpose || 'executive briefing',
            audience: detail.audience || 'officials',
            slide_count: slidesCount,
            duration: ctrls.duration || '10',
            language: detail.language || 'en',
            content_detail: ctrls.detail_level || 'balanced',
            theme: ctrls.theme || 'corporate_blue',
            visual_preference: ctrls.visual_preference || 'balanced',
            speaker_notes: ctrls.speaker_notes ?? true,
            additional_instructions: ctrls.additional_instructions || '',
          }
          setConfig(loadedConfig)
          setEditConfig(loadedConfig)
          setStep(5)
          setIsEditingWorkspace(true)
        })
        .catch((err) => {
          setError(err instanceof ApiError ? err.message : 'Failed to load presentation')
        })
    }
  }, [initialEditId])

  // Sync editConfig with config when opening edit workspace
  function handleOpenEditWorkspace() {
    setEditConfig({
      title: outputDetail?.content_ir.title || config.title,
      purpose: (outputDetail?.controls as any)?.purpose || config.purpose || 'executive briefing',
      audience: outputDetail?.audience || config.audience || 'officials',
      slide_count: String(outputDetail?.content_ir.nodes.filter((n) => n.kind === 'slide').length || 12),
      duration: (outputDetail?.controls as any)?.duration || config.duration || '10',
      language: outputDetail?.language || config.language || 'en',
      content_detail: outputDetail?.controls?.detail_level || config.content_detail || 'balanced',
      theme: (outputDetail?.controls as any)?.theme || config.theme || 'corporate_blue',
      visual_preference: (outputDetail?.controls as any)?.visual_preference || config.visual_preference || 'balanced',
      speaker_notes: config.speaker_notes ?? true,
      additional_instructions: config.additional_instructions || '',
    })
    setIsEditingWorkspace(true)
  }

  // File Upload Handler
  async function handleFileUpload(file: File) {
    setUploading(true)
    setError(null)
    try {
      const res = await api.uploadDocument(file)
      setUploadDoc(res.document)
      await api.streamJob(res.job.id, () => {})
      const updatedDoc = await api.getDocument(res.document.id)
      setUploadDoc(updatedDoc)
      setSelectedSourceId(updatedDoc.id)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  // Step 2 -> 3: Generate Outline
  async function handleGenerateOutline() {
    if (!selectedSourceId) return
    setGeneratingOutline(true)
    setError(null)
    try {
      const res = await api.generatePresentationOutline(selectedSourceId, config)
      setOutline(res)
      setStep(3)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Outline generation failed')
    } finally {
      setGeneratingOutline(false)
    }
  }

  // Outline Modification Helpers
  function handleUpdateOutlineItem(index: number, patch: Partial<SlideOutlineItem>) {
    if (!outline) return
    const updated = [...outline.slides]
    updated[index] = { ...updated[index], ...patch }
    setOutline({ ...outline, slides: updated })
  }

  function handleAddOutlineSlide() {
    if (!outline) return
    const newSlide: SlideOutlineItem = {
      id: `out_${outline.slides.length + 1}`,
      title: 'New Slide',
      key_message: 'Key message here',
      summary: 'Summary point',
      suggested_layout: 'standard_bullet',
    }
    setOutline({ ...outline, slides: [...outline.slides, newSlide] })
  }

  function handleDeleteOutlineSlide(index: number) {
    if (!outline) return
    setOutline({ ...outline, slides: outline.slides.filter((_, i) => i !== index) })
  }

  function handleMoveOutlineSlide(index: number, direction: 'up' | 'down') {
    if (!outline) return
    const slides = [...outline.slides]
    const targetIndex = direction === 'up' ? index - 1 : index + 1
    if (targetIndex < 0 || targetIndex >= slides.length) return
    const temp = slides[index]
    slides[index] = slides[targetIndex]
    slides[targetIndex] = temp
    setOutline({ ...outline, slides })
  }

  // Step 3 -> 4: Approve Outline & Generate Full Presentation
  async function handleApproveAndGenerateDeck() {
    if (!selectedSourceId) return
    setGeneratingDeck(true)
    setStep(4)
    setError(null)

    try {
      const startedJob = await api.generate(selectedSourceId, {
        types: ['ppt'],
        languages: [config.language || 'en'],
        audience: config.audience,
        controls: {
          detail_level: config.content_detail || 'balanced',
          theme: config.theme || 'corporate_blue',
        },
        options: {
          ppt: {
            slides: String(outline?.slides.length || 8),
            presenting_to: config.audience || 'officials',
          },
        },
      })
      setJob(startedJob)

      const finalJob = await api.streamJob(startedJob.id, setJob)
      if (finalJob.status === 'failed') {
        setError(finalJob.error ?? 'Generation failed')
        setStep(3)
        return
      }

      const outputId = finalJob.result?.outputs?.[0]
      if (outputId) {
        setCreatedOutputId(outputId)
        const detail = await api.getOutput(outputId)

        if (outline && detail.content_ir) {
          const updatedNodes = detail.content_ir.nodes.map((node, i) => {
            const outlineItem = outline.slides[i - 1]
            if (node.kind === 'slide' && outlineItem) {
              return { ...node, layout: outlineItem.suggested_layout || 'standard_bullet' }
            }
            return node
          })
          const updatedDetail = {
            ...detail,
            content_ir: { ...detail.content_ir, nodes: updatedNodes },
          }
          await api.updateOutput(outputId, updatedDetail.content_ir)
          setOutputDetail(updatedDetail)
        } else {
          setOutputDetail(detail)
        }

        onCreated([outputId])
        setStep(5)
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Generation failed')
      setStep(3)
    } finally {
      setGeneratingDeck(false)
    }
  }

  // --- SLIDE STUDIO & EDITING ACTIONS ---
  function selectSlideForEdit(index: number) {
    setActiveSlideIndex(index)
    if (!outputDetail) return
    const slides = outputDetail.content_ir.nodes.filter((n) => n.kind === 'slide')
    if (index === 0) {
      setEditingSlide(null)
    } else {
      setEditingSlide(slides[index - 1] || null)
    }
  }

  async function handleSaveSlideEdit(updatedNode: IRNode) {
    if (!outputDetail) return
    setSavingSlide(true)
    const nodeWithFlag: IRNode = { ...updatedNode, is_user_modified: true }
    try {
      const updatedNodes = outputDetail.content_ir.nodes.map((n) =>
        n.id === nodeWithFlag.id ? nodeWithFlag : n,
      )
      const updatedIR: ContentIR = { ...outputDetail.content_ir, nodes: updatedNodes }
      const res = await api.updateOutput(outputDetail.id, updatedIR)
      setOutputDetail(res)
      setEditingSlide(nodeWithFlag)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Save failed')
    } finally {
      setSavingSlide(false)
    }
  }

  async function handleSingleSlideRegenerate() {
    if (!outputDetail || !editingSlide) return
    setRegeneratingSlide(true)
    setError(null)
    try {
      const res = await api.regenerateSlide(outputDetail.id, editingSlide.id, slideInstructions)
      setOutputDetail(res)
      setSlideInstructions('')
      const updatedNode = res.content_ir.nodes.find((n) => n.id === editingSlide.id)
      if (updatedNode) setEditingSlide(updatedNode)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Single slide regeneration failed')
    } finally {
      setRegeneratingSlide(false)
    }
  }

  // Dynamic Add / Remove / Duplicate / Move Slide
  async function handleAddSlide(insertIndex?: number) {
    if (!outputDetail) return
    const slideNodes = outputDetail.content_ir.nodes.filter((n) => n.kind === 'slide')
    const titleNode = outputDetail.content_ir.nodes.find((n) => n.kind !== 'slide')
    const newSlideId = `slide_${Date.now()}`
    const newSlide: IRNode = {
      id: newSlideId,
      kind: 'slide',
      title: 'New Custom Slide',
      layout: 'standard_bullet',
      items: ['Key takeaway point 1', 'Supporting evidence or context'],
      notes: 'Speaker notes for new slide.',
      fact_ids: [],
      is_user_modified: true,
    }

    const updatedSlides = [...slideNodes]
    const idx = insertIndex !== undefined ? insertIndex : updatedSlides.length
    updatedSlides.splice(idx, 0, newSlide)

    const updatedNodes = titleNode ? [titleNode, ...updatedSlides] : updatedSlides
    const updatedIR: ContentIR = { ...outputDetail.content_ir, nodes: updatedNodes }

    try {
      const res = await api.updateOutput(outputDetail.id, updatedIR)
      setOutputDetail(res)
      setActiveSlideIndex(idx + 1)
      setEditingSlide(newSlide)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Add slide failed')
    }
  }

  async function handleDeleteSlide(slideId: string) {
    if (!outputDetail) return
    const updatedNodes = outputDetail.content_ir.nodes.filter((n) => n.id !== slideId)
    const updatedIR: ContentIR = { ...outputDetail.content_ir, nodes: updatedNodes }

    try {
      const res = await api.updateOutput(outputDetail.id, updatedIR)
      setOutputDetail(res)
      const remainingSlides = updatedNodes.filter((n) => n.kind === 'slide')
      if (remainingSlides.length > 0) {
        setActiveSlideIndex(1)
        setEditingSlide(remainingSlides[0])
      } else {
        setActiveSlideIndex(0)
        setEditingSlide(null)
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Delete slide failed')
    }
  }

  async function handleDuplicateSlide(slideNode: IRNode) {
    if (!outputDetail) return
    const slideNodes = outputDetail.content_ir.nodes.filter((n) => n.kind === 'slide')
    const slideIdx = slideNodes.findIndex((s) => s.id === slideNode.id)
    const titleNode = outputDetail.content_ir.nodes.find((n) => n.kind !== 'slide')

    const dupSlide: IRNode = {
      ...slideNode,
      id: `slide_${Date.now()}`,
      title: `${slideNode.title || 'Slide'} (Copy)`,
      is_user_modified: true,
    }

    const updatedSlides = [...slideNodes]
    updatedSlides.splice(slideIdx + 1, 0, dupSlide)

    const updatedNodes = titleNode ? [titleNode, ...updatedSlides] : updatedSlides
    const updatedIR: ContentIR = { ...outputDetail.content_ir, nodes: updatedNodes }

    try {
      const res = await api.updateOutput(outputDetail.id, updatedIR)
      setOutputDetail(res)
      setActiveSlideIndex(slideIdx + 2)
      setEditingSlide(dupSlide)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Duplicate slide failed')
    }
  }

  async function handleMoveSlide(index: number, direction: 'up' | 'down') {
    if (!outputDetail) return
    const slideNodes = outputDetail.content_ir.nodes.filter((n) => n.kind === 'slide')
    const titleNode = outputDetail.content_ir.nodes.find((n) => n.kind !== 'slide')

    const targetIndex = direction === 'up' ? index - 1 : index + 1
    if (targetIndex < 0 || targetIndex >= slideNodes.length) return

    const updatedSlides = [...slideNodes]
    const temp = updatedSlides[index]
    updatedSlides[index] = updatedSlides[targetIndex]
    updatedSlides[targetIndex] = temp

    const updatedNodes = titleNode ? [titleNode, ...updatedSlides] : updatedSlides
    const updatedIR: ContentIR = { ...outputDetail.content_ir, nodes: updatedNodes }

    try {
      const res = await api.updateOutput(outputDetail.id, updatedIR)
      setOutputDetail(res)
      setActiveSlideIndex(targetIndex + 1)
      setEditingSlide(updatedSlides[targetIndex])
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Reorder slide failed')
    }
  }

  // --- EDIT PRESENTATION RECONFIGURATION ACTIONS ---
  async function handleApplyThemeChange(newTheme: string) {
    if (!outputDetail) return
    setConfig((prev) => ({ ...prev, theme: newTheme }))
    setEditConfig((prev) => ({ ...prev, theme: newTheme }))

    try {
      const res = await api.reconfigurePresentation(outputDetail.id, {
        config: { ...editConfig, theme: newTheme },
        scope: 'all',
        preserve_user_edits: true,
        content_ir: outputDetail.content_ir,
      })
      setOutputDetail(res.output)
      if (res.change_summary.length > 0) {
        setChangeSummary(res.change_summary)
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Theme update failed')
    }
  }

  async function handleReconfigureContent() {
    if (!outputDetail) return
    setReconfiguring(true)
    setError(null)
    try {
      const res = await api.reconfigurePresentation(outputDetail.id, {
        config: editConfig,
        scope: reconfigScope,
        selected_slide_ids: reconfigScope === 'selected' ? selectedSlideIdsForRegen : undefined,
        preserve_user_edits: preserveUserEdits,
        content_ir: outputDetail.content_ir,
      })
      setOutputDetail(res.output)
      setConfig(editConfig)
      setChangeSummary(res.change_summary)
      setShowReconfigModal(false)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Reconfiguration failed')
    } finally {
      setReconfiguring(false)
    }
  }

  async function handleAdjustSlideCount() {
    if (!outputDetail) return
    setAdjustingCount(true)
    setError(null)
    try {
      const proposed = await api.adjustSlideCount(outputDetail.id, {
        target_count: editConfig.slide_count || '12',
        config: editConfig,
      })
      setProposedOutline(proposed)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Slide count adjustment failed')
    } finally {
      setAdjustingCount(false)
    }
  }

  async function handleApproveSlideCountAdjustment() {
    if (!outputDetail || !proposedOutline) return
    setReconfiguring(true)
    setError(null)
    try {
      const res = await api.reconfigurePresentation(outputDetail.id, {
        config: editConfig,
        scope: 'all',
        preserve_user_edits: preserveUserEdits,
        content_ir: outputDetail.content_ir,
      })
      setOutputDetail(res.output)
      setConfig(editConfig)
      setChangeSummary(res.change_summary)
      setProposedOutline(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Outline approval failed')
    } finally {
      setReconfiguring(false)
    }
  }

  async function handleRevertVersion() {
    if (!outputDetail) return
    setReverting(true)
    setError(null)
    try {
      const res = await api.revertPresentation(outputDetail.id)
      setOutputDetail(res)
      setChangeSummary(['Reverted presentation to previous version successfully.'])
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Revert failed')
    } finally {
      setReverting(false)
    }
  }

  async function handleDownloadPPTX() {
    if (!outputDetail) return
    setExporting(true)
    try {
      const blobUrl = await api.exportUrl(
        outputDetail.id,
        'pptx',
        false,
        config.theme || (outputDetail.controls as any)?.theme || 'navy_white',
      )
      const link = document.createElement('a')
      link.href = blobUrl
      const filename = `${(outputDetail.content_ir.title || 'presentation').toLowerCase().replace(/[^a-z0-9]+/g, '_')}.pptx`
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Download failed')
    } finally {
      setExporting(false)
    }
  }

  const activeDocName =
    sources.find((d) => d.id === selectedSourceId)?.filename || uploadDoc?.filename || 'Source Document'

  const userModifiedCount =
    outputDetail?.content_ir.nodes.filter((n) => n.kind === 'slide' && n.is_user_modified).length || 0

  return (
    <div className="space-y-6 rounded-2xl border border-ink-200 bg-white p-6 shadow-sm">
      {/* Step Progress Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-ink-100 pb-4">
        <div className="flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-brand-600">
            <Icon name="ppt" className="h-5 w-5" />
          </span>
          <div>
            <h2 className="text-lg font-bold tracking-tight text-ink-900">
              AI Presentation Studio
            </h2>
            <p className="text-xs text-ink-500">
              {step === 1 && 'Step 1: Upload or select a source document'}
              {step === 2 && 'Step 2: Configure presentation parameters'}
              {step === 3 && 'Step 3: Review and edit AI slide outline'}
              {step === 4 && 'Step 4: Generating PowerPoint presentation'}
              {step === 5 && !isEditingWorkspace && 'Step 5: Interactive Slide Studio & Export'}
              {step === 5 && isEditingWorkspace && 'Presentation Editor: Modify Configuration & Slide Details'}
            </p>
          </div>
        </div>

        {/* Step Indicator Badges */}
        <div className="flex items-center gap-1.5 text-xs font-medium">
          {[
            { num: 1, label: 'Source' },
            { num: 2, label: 'Configure' },
            { num: 3, label: 'Outline' },
            { num: 4, label: 'Generate' },
            { num: 5, label: isEditingWorkspace ? 'Editor Workspace' : 'Preview & Export' },
          ].map((s) => (
            <button
              key={s.num}
              disabled={s.num > step && step !== 5}
              onClick={() => {
                if (s.num < step) {
                  setIsEditingWorkspace(false)
                  setStep(s.num as any)
                }
              }}
              className={`flex items-center gap-1 rounded-lg px-2.5 py-1 transition ${
                step === s.num
                  ? 'bg-brand-600 text-white shadow-xs'
                  : step > s.num
                    ? 'bg-ink-100 text-ink-700 hover:bg-ink-200'
                    : 'text-ink-400 opacity-60'
              }`}
            >
              <span>{s.num}.</span>
              <span className="hidden sm:inline">{s.label}</span>
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-700 flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-500 font-bold ml-2">✕</button>
        </div>
      )}

      {/* STEP 1: SOURCE SELECTION & UPLOAD */}
      {step === 1 && (
        <div className="space-y-6 py-2">
          <div className="grid gap-6 md:grid-cols-2">
            <div className="space-y-3 rounded-xl border border-ink-200 p-4">
              <h3 className="text-sm font-semibold text-ink-900">Select Existing Document</h3>
              <p className="text-xs text-ink-500">
                Choose a pre-processed document from your repository.
              </p>
              {readySources.length > 0 ? (
                <Select
                  value={selectedSourceId}
                  onChange={setSelectedSourceId}
                  options={readySources.map((d) => ({ key: d.id, label: d.filename }))}
                />
              ) : (
                <p className="text-xs text-ink-400 italic">No ready documents found.</p>
              )}
            </div>

            <div className="space-y-3 rounded-xl border border-dashed border-ink-300 p-4 text-center">
              <h3 className="text-sm font-semibold text-ink-900">Upload New Source Document</h3>
              <p className="text-xs text-ink-500">Support PDF, DOCX, TXT, or scanned files.</p>
              <label className="inline-flex cursor-pointer items-center justify-center gap-2 rounded-xl bg-ink-100 px-4 py-2 text-xs font-medium text-ink-800 hover:bg-ink-200">
                <Icon name="plus" />
                {uploading ? 'Processing File…' : 'Choose File to Upload'}
                <input
                  type="file"
                  className="hidden"
                  accept=".pdf,.docx,.txt,image/*"
                  onChange={(e) => {
                    if (e.target.files?.[0]) handleFileUpload(e.target.files[0])
                  }}
                  disabled={uploading}
                />
              </label>
            </div>
          </div>

          {selectedSourceId && (
            <div className="flex items-center justify-between rounded-xl bg-blue-50/60 p-4 border border-blue-100">
              <div className="flex items-center gap-3">
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-100 text-brand-600 font-semibold text-xs">
                  DOC
                </span>
                <div>
                  <p className="text-xs font-bold text-ink-900">{activeDocName}</p>
                  <p className="text-[11px] text-ink-500">Source verified & key facts ready for presentation synthesis.</p>
                </div>
              </div>
              <Button onClick={() => setStep(2)}>
                Continue to Configuration
                <Icon name="spark" />
              </Button>
            </div>
          )}
        </div>
      )}

      {/* STEP 2: PRESENTATION CONFIGURATION */}
      {step === 2 && (
        <div className="space-y-6 py-2">
          <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
            <Field label="Presentation Title (Optional)">
              <input
                type="text"
                value={config.title || ''}
                onChange={(e) => setConfig({ ...config, title: e.target.value })}
                placeholder="Leave blank for AI auto-title"
                className="w-full rounded-lg border border-ink-200 px-3 py-2 text-xs outline-none focus:border-brand-500"
              />
            </Field>

            <Field label="Purpose">
              <Select
                value={config.purpose || 'executive briefing'}
                onChange={(v) => setConfig({ ...config, purpose: v })}
                options={PURPOSES}
              />
            </Field>

            <Field label="Target Audience">
              <Select
                value={config.audience || 'officials'}
                onChange={(v) => setConfig({ ...config, audience: v })}
                options={AUDIENCES}
              />
            </Field>

            <Field label="Slide Count">
              <Segmented
                options={SLIDE_COUNTS}
                value={config.slide_count || 'auto'}
                onChange={(v) => setConfig({ ...config, slide_count: v })}
              />
            </Field>

            <Field label="Estimated Duration">
              <Segmented
                options={DURATIONS}
                value={config.duration || '10'}
                onChange={(v) => setConfig({ ...config, duration: v })}
              />
            </Field>

            <Field label="Language">
              <Segmented
                options={languages.map((code) => ({ key: code, label: code.toUpperCase() }))}
                value={config.language || 'en'}
                onChange={(v) => setConfig({ ...config, language: v })}
              />
            </Field>

            <Field label="Content Detail Level">
              <Segmented
                options={[
                  { key: 'concise', label: 'Concise' },
                  { key: 'balanced', label: 'Balanced' },
                  { key: 'detailed', label: 'Detailed' },
                ]}
                value={config.content_detail || 'balanced'}
                onChange={(v) => setConfig({ ...config, content_detail: v })}
              />
            </Field>

            <Field label="Visual Theme">
              <Select
                value={config.theme || 'corporate_blue'}
                onChange={(v) => setConfig({ ...config, theme: v })}
                options={THEMES}
              />
            </Field>

            <Field label="Speaker Notes">
              <label className="flex items-center gap-2 pt-2 text-xs font-medium text-ink-800">
                <input
                  type="checkbox"
                  checked={config.speaker_notes ?? true}
                  onChange={(e) => setConfig({ ...config, speaker_notes: e.target.checked })}
                  className="h-4 w-4 rounded border-ink-300 text-brand-600 focus:ring-brand-500"
                />
                Generate speaker notes for each slide
              </label>
            </Field>
          </div>

          <Field label="Additional Instructions (Optional)">
            <textarea
              value={config.additional_instructions || ''}
              onChange={(e) => setConfig({ ...config, additional_instructions: e.target.value })}
              rows={2}
              placeholder="e.g. Focus on cybersecurity risks, mitigation timeline, and budget requirements."
              className="w-full rounded-lg border border-ink-200 px-3 py-2 text-xs outline-none focus:border-brand-500"
            />
          </Field>

          <div className="flex items-center justify-between border-t border-ink-100 pt-4">
            <Button variant="ghost" onClick={() => setStep(1)}>
              Back
            </Button>
            <Button onClick={handleGenerateOutline} disabled={generatingOutline}>
              <Icon name="spark" />
              {generatingOutline ? 'Structuring Outline…' : 'Generate AI Slide Outline'}
            </Button>
          </div>
        </div>
      )}

      {/* STEP 3: AI SLIDE OUTLINE REVIEW */}
      {step === 3 && outline && (
        <div className="space-y-6 py-2">
          <div className="flex items-center justify-between">
            <Field label="Presentation Outline Title">
              <input
                type="text"
                value={outline.title}
                onChange={(e) => setOutline({ ...outline, title: e.target.value })}
                className="w-full max-w-md rounded-lg border border-ink-200 px-3 py-1.5 text-sm font-bold outline-none focus:border-brand-500"
              />
            </Field>
            <Button variant="secondary" onClick={handleAddOutlineSlide}>
              <Icon name="plus" />
              Add Slide Card
            </Button>
          </div>

          <div className="space-y-3">
            {outline.slides.map((item, idx) => (
              <div
                key={item.id || idx}
                className="flex flex-col gap-3 rounded-xl border border-ink-200 bg-white p-4 shadow-xs md:flex-row md:items-start"
              >
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-ink-100 text-xs font-bold text-ink-700">
                  {idx + 1}
                </span>

                <div className="grid flex-1 gap-3 sm:grid-cols-2">
                  <label className="block">
                    <span className="text-[11px] font-medium text-ink-400">Slide Title</span>
                    <input
                      type="text"
                      value={item.title}
                      onChange={(e) => handleUpdateOutlineItem(idx, { title: e.target.value })}
                      className="mt-1 w-full rounded-md border border-ink-200 px-2.5 py-1 text-xs font-semibold outline-none focus:border-brand-500"
                    />
                  </label>

                  <label className="block">
                    <span className="text-[11px] font-medium text-ink-400">Suggested Layout</span>
                    <Select
                      value={item.suggested_layout || 'standard_bullet'}
                      onChange={(v) => handleUpdateOutlineItem(idx, { suggested_layout: v })}
                      options={LAYOUT_OPTIONS}
                    />
                  </label>

                  <label className="block sm:col-span-2">
                    <span className="text-[11px] font-medium text-ink-400">Key Message & Summary</span>
                    <textarea
                      value={item.summary || item.key_message}
                      onChange={(e) => handleUpdateOutlineItem(idx, { summary: e.target.value })}
                      rows={2}
                      className="mt-1 w-full rounded-md border border-ink-200 px-2.5 py-1 text-xs outline-none focus:border-brand-500"
                    />
                  </label>
                </div>

                <div className="flex items-center gap-1 self-end md:self-start">
                  <button
                    disabled={idx === 0}
                    onClick={() => handleMoveOutlineSlide(idx, 'up')}
                    className="rounded p-1 text-ink-400 hover:bg-ink-100 hover:text-ink-800 disabled:opacity-30"
                    title="Move Up"
                  >
                    ↑
                  </button>
                  <button
                    disabled={idx === outline.slides.length - 1}
                    onClick={() => handleMoveOutlineSlide(idx, 'down')}
                    className="rounded p-1 text-ink-400 hover:bg-ink-100 hover:text-ink-800 disabled:opacity-30"
                    title="Move Down"
                  >
                    ↓
                  </button>
                  <button
                    onClick={() => handleDeleteOutlineSlide(idx)}
                    className="rounded p-1 text-red-500 hover:bg-red-50"
                    title="Delete Slide"
                  >
                    ✕
                  </button>
                </div>
              </div>
            ))}
          </div>

          <div className="flex items-center justify-between border-t border-ink-100 pt-4">
            <Button variant="ghost" onClick={() => setStep(2)}>
              Back to Config
            </Button>
            <div className="flex items-center gap-2">
              <Button variant="secondary" onClick={handleGenerateOutline} disabled={generatingOutline}>
                Regenerate Outline
              </Button>
              <Button onClick={handleApproveAndGenerateDeck} disabled={generatingDeck}>
                <Icon name="spark" />
                Approve & Generate Presentation ({outline.slides.length} Slides)
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* STEP 4: GENERATING DECK */}
      {step === 4 && (
        <div className="space-y-6 py-8 text-center">
          <div className="mx-auto max-w-md space-y-4">
            <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-50 text-brand-600 mx-auto animate-pulse">
              <Icon name="spark" className="h-6 w-6" />
            </span>
            <h3 className="text-base font-bold text-ink-900">Synthesizing Full Slide Deck</h3>
            <Progress value={job?.progress ?? 0.3} label={job?.stage ?? 'Writing slides…'} />
            <p className="text-xs text-ink-500">
              Structuring content, formatting speaker notes, and applying {config.theme} visual theme...
            </p>
          </div>
        </div>
      )}

      {/* STEP 5: INTERACTIVE SLIDE STUDIO PREVIEW, EDIT WORKSPACE & EXPORT */}
      {step === 5 && outputDetail && (
        <div className="space-y-6">
          {/* Change Summary Banner */}
          {changeSummary.length > 0 && (
            <div className="rounded-xl border border-emerald-200 bg-emerald-50/70 p-4">
              <div className="flex items-center justify-between pb-1">
                <h4 className="text-xs font-bold text-emerald-900 flex items-center gap-1.5">
                  <Icon name="check" className="h-4 w-4 text-emerald-600" />
                  Presentation Reconfigured Successfully
                </h4>
                <button
                  onClick={() => setChangeSummary([])}
                  className="text-emerald-700 hover:text-emerald-900 text-xs"
                >
                  Dismiss
                </button>
              </div>
              <ul className="list-disc list-inside text-xs text-emerald-800 space-y-0.5 mt-1">
                {changeSummary.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Top Bar Navigation & Actions */}
          <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-ink-200 bg-ink-50 p-3">
            <div className="flex items-center gap-3">
              <span className="text-xs font-semibold text-ink-800">Theme:</span>
              <Select
                value={config.theme || (outputDetail.controls as any)?.theme || 'corporate_blue'}
                onChange={(v) => handleApplyThemeChange(v)}
                options={THEMES}
              />
              {outputDetail.version > 1 && (
                <Button
                  variant="secondary"
                  onClick={handleRevertVersion}
                  disabled={reverting}
                  className="text-xs"
                >
                  <Icon name="back" className="h-3.5 w-3.5" />
                  {reverting ? 'Reverting…' : `Revert (v${outputDetail.version - 1})`}
                </Button>
              )}
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant={isEditingWorkspace ? 'secondary' : 'primary'}
                onClick={() => {
                  if (isEditingWorkspace) {
                    setIsEditingWorkspace(false)
                  } else {
                    handleOpenEditWorkspace()
                  }
                }}
              >
                <Icon name="edit" className="h-4 w-4" />
                {isEditingWorkspace ? 'Exit Editor & Preview' : 'Edit Presentation'}
              </Button>

              <Button onClick={handleDownloadPPTX} disabled={exporting}>
                <Icon name="download" className="h-4 w-4" />
                {exporting ? 'Preparing PPTX…' : 'Download PowerPoint (.pptx)'}
              </Button>
            </div>
          </div>

          {/* EDIT WORKSPACE vs REGULAR PREVIEW */}
          {isEditingWorkspace ? (
            <div className="space-y-6 border-t border-ink-200 pt-4">
              {/* EDITABLE SETTINGS PANEL */}
              <div className="rounded-2xl border border-brand-200 bg-blue-50/30 p-5 space-y-4">
                <div className="flex items-center justify-between border-b border-brand-100 pb-3">
                  <div>
                    <h3 className="text-sm font-bold text-ink-900 flex items-center gap-2">
                      <Icon name="edit" className="text-brand-600 h-4 w-4" />
                      Presentation Settings & Parameters
                    </h3>
                    <p className="text-xs text-ink-500">
                      Modify global presentation settings. Settings apply across your slide deck.
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="secondary"
                      onClick={() => setShowReconfigModal(true)}
                      disabled={reconfiguring}
                    >
                      <Icon name="spark" />
                      Apply & Regenerate Content
                    </Button>
                  </div>
                </div>

                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  <Field label="Presentation Title">
                    <input
                      type="text"
                      value={editConfig.title || ''}
                      onChange={(e) => setEditConfig({ ...editConfig, title: e.target.value })}
                      className="w-full rounded-lg border border-ink-200 bg-white px-3 py-1.5 text-xs outline-none focus:border-brand-500"
                    />
                  </Field>

                  <Field label="Purpose">
                    <Select
                      value={editConfig.purpose || 'executive briefing'}
                      onChange={(v) => setEditConfig({ ...editConfig, purpose: v })}
                      options={PURPOSES}
                    />
                  </Field>

                  <Field label="Target Audience">
                    <Select
                      value={editConfig.audience || 'officials'}
                      onChange={(v) => setEditConfig({ ...editConfig, audience: v })}
                      options={AUDIENCES}
                    />
                  </Field>

                  <Field label="Slide Count">
                    <div className="flex items-center gap-2">
                      <div className="flex-1">
                        <Select
                          value={editConfig.slide_count || '12'}
                          onChange={(v) => {
                            setEditConfig({ ...editConfig, slide_count: v })
                          }}
                          options={SLIDE_COUNTS}
                        />
                      </div>
                      <Button
                        variant="secondary"
                        onClick={handleAdjustSlideCount}
                        disabled={adjustingCount}
                        className="shrink-0 text-xs px-2.5"
                      >
                        {adjustingCount ? 'Proposing…' : 'Propose Outline'}
                      </Button>
                    </div>
                  </Field>

                  <Field label="Estimated Duration">
                    <Select
                      value={editConfig.duration || '10'}
                      onChange={(v) => setEditConfig({ ...editConfig, duration: v })}
                      options={DURATIONS}
                    />
                  </Field>

                  <Field label="Language">
                    <Select
                      value={editConfig.language || 'en'}
                      onChange={(v) => setEditConfig({ ...editConfig, language: v })}
                      options={languages.map((c) => ({ key: c, label: c.toUpperCase() }))}
                    />
                  </Field>

                  <Field label="Detail Level">
                    <Segmented
                      options={[
                        { key: 'concise', label: 'Concise' },
                        { key: 'balanced', label: 'Balanced' },
                        { key: 'detailed', label: 'Detailed' },
                      ]}
                      value={editConfig.content_detail || 'balanced'}
                      onChange={(v) => setEditConfig({ ...editConfig, content_detail: v })}
                    />
                  </Field>

                  <Field label="Visual Theme">
                    <Select
                      value={editConfig.theme || 'corporate_blue'}
                      onChange={(v) => handleApplyThemeChange(v)}
                      options={THEMES}
                    />
                  </Field>

                  <Field label="Visual Preference">
                    <Segmented
                      options={[
                        { key: 'text-focused', label: 'Text-Focused' },
                        { key: 'balanced', label: 'Balanced' },
                        { key: 'visual-heavy', label: 'Visual-Heavy' },
                      ]}
                      value={editConfig.visual_preference || 'balanced'}
                      onChange={(v) => setEditConfig({ ...editConfig, visual_preference: v })}
                    />
                  </Field>
                </div>

                <Field label="Additional AI Instructions">
                  <textarea
                    value={editConfig.additional_instructions || ''}
                    onChange={(e) => setEditConfig({ ...editConfig, additional_instructions: e.target.value })}
                    rows={2}
                    placeholder="Specific requests for regeneration..."
                    className="w-full rounded-lg border border-ink-200 bg-white px-3 py-1.5 text-xs outline-none focus:border-brand-500"
                  />
                </Field>
              </div>

              {/* SLIDE COUNT ADJUSTMENT PROPOSAL BOX */}
              {proposedOutline && (
                <div className="rounded-2xl border border-indigo-200 bg-indigo-50/80 p-5 space-y-4 shadow-sm">
                  <div className="flex items-center justify-between border-b border-indigo-200 pb-3">
                    <div>
                      <h4 className="text-sm font-bold text-indigo-900 flex items-center gap-2">
                        <Icon name="spark" className="text-indigo-600 h-4 w-4" />
                        Proposed Outline Adjustment ({proposedOutline.slides.length} Total Slides)
                      </h4>
                      <p className="text-xs text-indigo-700">
                        Review the proposed slide outline additions or removals before generating.
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="secondary"
                        onClick={() => setProposedOutline(null)}
                      >
                        Cancel
                      </Button>
                      <Button
                        onClick={handleApproveSlideCountAdjustment}
                        disabled={reconfiguring}
                      >
                        {reconfiguring ? 'Applying Outline…' : 'Approve & Update Deck'}
                      </Button>
                    </div>
                  </div>

                  <div className="grid gap-2 max-h-60 overflow-y-auto pr-2">
                    {proposedOutline.slides.map((s, idx) => (
                      <div
                        key={s.id || idx}
                        className="flex items-center justify-between rounded-lg border border-indigo-200 bg-white p-2.5 text-xs"
                      >
                        <span className="font-bold text-indigo-900 w-8">#{idx + 1}</span>
                        <div className="flex-1 font-semibold text-ink-900 px-2">{s.title}</div>
                        <div className="text-[11px] text-ink-500 bg-indigo-50 px-2 py-0.5 rounded">
                          {s.suggested_layout || 'standard_bullet'}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* INDIVIDUAL SLIDES SIDEBAR & CANVAS EDITOR */}
              <div className="grid gap-6 lg:grid-cols-[18rem_minmax(0,1fr)]">
                {/* Slide Thumbnails & Management Sidebar */}
                <div className="space-y-3 rounded-xl border border-ink-200 bg-white p-3 shadow-xs">
                  <div className="flex items-center justify-between border-b border-ink-100 pb-2">
                    <span className="text-xs font-bold text-ink-900">
                      Slides ({outputDetail.content_ir.nodes.filter((n) => n.kind === 'slide').length + 1})
                    </span>
                    <Button
                      variant="secondary"
                      onClick={() => handleAddSlide()}
                      className="text-[11px] py-1 px-2"
                    >
                      <Icon name="plus" className="h-3 w-3" />
                      Add Slide
                    </Button>
                  </div>

                  <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
                    {/* Cover Slide Thumbnail */}
                    <button
                      onClick={() => selectSlideForEdit(0)}
                      className={`w-full flex items-center justify-between rounded-lg border p-2.5 text-left text-xs transition ${
                        activeSlideIndex === 0
                          ? 'border-brand-600 bg-blue-50/80 font-bold text-brand-700 ring-2 ring-brand-300'
                          : 'border-ink-200 bg-white text-ink-800 hover:bg-ink-50'
                      }`}
                    >
                      <div className="flex items-center gap-2 truncate">
                        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded bg-ink-100 text-[10px] font-bold text-ink-600">
                          1
                        </span>
                        <span className="truncate font-semibold">{outputDetail.content_ir.title || 'Title Slide'}</span>
                      </div>
                      <span className="text-[9px] bg-ink-100 text-ink-600 px-1.5 py-0.5 rounded">Cover</span>
                    </button>

                    {/* Slide Nodes Thumbnails */}
                    {outputDetail.content_ir.nodes
                      .filter((n) => n.kind === 'slide')
                      .map((node, i) => (
                        <div
                          key={node.id}
                          onClick={() => selectSlideForEdit(i + 1)}
                          className={`flex items-center justify-between rounded-lg border p-2 text-xs cursor-pointer transition ${
                            activeSlideIndex === i + 1
                              ? 'border-brand-600 bg-blue-50/80 font-bold text-brand-700 ring-2 ring-brand-300'
                              : 'border-ink-200 bg-white text-ink-800 hover:bg-ink-50'
                          }`}
                        >
                          <div className="flex items-center gap-2 truncate flex-1 min-w-0">
                            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded bg-ink-100 text-[10px] font-bold text-ink-600">
                              {i + 2}
                            </span>
                            <div className="truncate flex-1">
                              <p className="truncate font-semibold text-xs">{node.title || 'Untitled Slide'}</p>
                              <div className="flex items-center gap-1 mt-0.5">
                                <span className="text-[9px] text-ink-500 bg-ink-100 px-1 py-0.2 rounded capitalize">
                                  {node.layout || 'bullets'}
                                </span>
                                {node.is_user_modified && (
                                  <span className="text-[9px] bg-amber-100 text-amber-800 font-bold px-1 rounded">
                                    Edited
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>

                          {/* Action icons */}
                          <div className="flex items-center gap-1 shrink-0 ml-1">
                            <button
                              disabled={i === 0}
                              onClick={(e) => {
                                e.stopPropagation()
                                handleMoveSlide(i, 'up')
                              }}
                              className="rounded p-0.5 text-ink-400 hover:bg-ink-200 disabled:opacity-20 text-[10px]"
                              title="Move Up"
                            >
                              ↑
                            </button>
                            <button
                              disabled={i === outputDetail.content_ir.nodes.filter((n) => n.kind === 'slide').length - 1}
                              onClick={(e) => {
                                e.stopPropagation()
                                handleMoveSlide(i, 'down')
                              }}
                              className="rounded p-0.5 text-ink-400 hover:bg-ink-200 disabled:opacity-20 text-[10px]"
                              title="Move Down"
                            >
                              ↓
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                handleDuplicateSlide(node)
                              }}
                              className="rounded p-0.5 text-blue-600 hover:bg-blue-100 text-[10px]"
                              title="Duplicate Slide"
                            >
                              📋
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                handleDeleteSlide(node.id)
                              }}
                              className="rounded p-0.5 text-red-500 hover:bg-red-100 text-[10px]"
                              title="Delete Slide"
                            >
                              ✕
                            </button>
                          </div>
                        </div>
                      ))}
                  </div>
                </div>

                {/* Main Editing Canvas Panel */}
                <div className="space-y-4 rounded-xl border border-ink-200 bg-white p-5 shadow-xs">
                  <div className="flex items-center justify-between border-b border-ink-100 pb-3">
                    <h3 className="text-sm font-bold text-ink-900 flex items-center gap-2">
                      {activeSlideIndex === 0 ? 'Cover Slide Details' : `Slide ${activeSlideIndex + 1} Content & Layout`}
                      {editingSlide?.is_user_modified && (
                        <span className="text-xs bg-amber-100 text-amber-800 font-semibold px-2 py-0.5 rounded-full">
                          Manually Edited
                        </span>
                      )}
                    </h3>

                    {activeSlideIndex > 0 && editingSlide && (
                      <div className="flex items-center gap-2">
                        <Button
                          variant="secondary"
                          onClick={() => handleDuplicateSlide(editingSlide)}
                          className="text-xs py-1 px-2.5"
                        >
                          Duplicate
                        </Button>
                        <Button
                          variant="secondary"
                          onClick={() => handleDeleteSlide(editingSlide.id)}
                          className="text-xs py-1 px-2.5 text-red-600 border-red-200 hover:bg-red-50"
                        >
                          Delete
                        </Button>
                      </div>
                    )}
                  </div>

                  {activeSlideIndex === 0 ? (
                    <div className="space-y-4">
                      <Field label="Presentation Title">
                        <input
                          type="text"
                          value={outputDetail.content_ir.title}
                          onChange={(e) => {
                            const updated = { ...outputDetail.content_ir, title: e.target.value }
                            setOutputDetail({ ...outputDetail, content_ir: updated })
                            api.updateOutput(outputDetail.id, updated)
                          }}
                          className="w-full rounded-md border border-ink-200 px-3 py-2 text-xs font-semibold outline-none focus:border-brand-500"
                        />
                      </Field>
                    </div>
                  ) : editingSlide ? (
                    <div className="space-y-4">
                      <div className="grid gap-4 sm:grid-cols-2">
                        <Field label="Slide Title">
                          <input
                            type="text"
                            value={editingSlide.title || ''}
                            onChange={(e) => {
                              const updated = { ...editingSlide, title: e.target.value }
                              setEditingSlide(updated)
                              handleSaveSlideEdit(updated)
                            }}
                            className="w-full rounded-md border border-ink-200 px-3 py-1.5 text-xs font-semibold outline-none focus:border-brand-500"
                          />
                        </Field>

                        <Field label="Slide Layout Type">
                          <Select
                            value={editingSlide.layout || 'standard_bullet'}
                            onChange={(v) => {
                              const updated = { ...editingSlide, layout: v }
                              setEditingSlide(updated)
                              handleSaveSlideEdit(updated)
                            }}
                            options={LAYOUT_OPTIONS}
                          />
                        </Field>
                      </div>

                      {/* Content Bullet Items Textarea */}
                      <Field label="Content Blocks / Bullets (One item per line)">
                        <textarea
                          value={(editingSlide.items || []).join('\n')}
                          onChange={(e) => {
                            const updated = {
                              ...editingSlide,
                              items: e.target.value.split('\n'),
                            }
                            setEditingSlide(updated)
                            handleSaveSlideEdit(updated)
                          }}
                          rows={6}
                          placeholder="Enter bullet points, metrics (Value | Label | Context), or timeline events (Date | Event | Detail)..."
                          className="w-full rounded-md border border-ink-200 px-3 py-2 text-xs outline-none focus:border-brand-500 font-mono"
                        />
                        <p className="text-[10px] text-ink-400 mt-1">
                          Tip for timelines/metrics: Format as <code className="bg-ink-100 px-1 rounded">Label | Description</code> or <code className="bg-ink-100 px-1 rounded">Value | Title | Details</code>.
                        </p>
                      </Field>

                      <Field label="Speaker Notes">
                        <textarea
                          value={editingSlide.notes || ''}
                          onChange={(e) => {
                            const updated = { ...editingSlide, notes: e.target.value }
                            setEditingSlide(updated)
                            handleSaveSlideEdit(updated)
                          }}
                          rows={3}
                          placeholder="Speaker narrative notes..."
                          className="w-full rounded-md border border-ink-200 px-3 py-2 text-xs outline-none focus:border-brand-500"
                        />
                      </Field>

                      {/* Single Slide AI Regeneration Panel */}
                      <div className="rounded-xl border border-blue-100 bg-blue-50/60 p-4 space-y-3">
                        <div className="flex items-center justify-between">
                          <h4 className="text-xs font-bold text-brand-800 flex items-center gap-1.5">
                            <Icon name="spark" className="h-4 w-4 text-brand-600" />
                            Regenerate This Slide with AI
                          </h4>
                          <span className="text-[10px] text-ink-500">Uses source facts</span>
                        </div>
                        <textarea
                          value={slideInstructions}
                          onChange={(e) => setSlideInstructions(e.target.value)}
                          placeholder="e.g. Expand into a detailed timeline with specific dates, or emphasize mitigation stats."
                          rows={2}
                          className="w-full rounded-md border border-ink-200 bg-white px-3 py-1.5 text-xs outline-none focus:border-brand-500"
                        />
                        <Button
                          variant="secondary"
                          onClick={handleSingleSlideRegenerate}
                          disabled={regeneratingSlide}
                          className="w-full justify-center"
                        >
                          {regeneratingSlide ? 'Regenerating Slide…' : 'Regenerate This Slide'}
                        </Button>
                      </div>
                    </div>
                  ) : null}
                </div>
              </div>
            </div>
          ) : (
            /* REGULAR PRESENTATION PREVIEW MODE */
            <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_18rem]">
              <div className="space-y-4">
                <DeckPreview
                  ir={outputDetail.content_ir}
                  theme={config.theme || (outputDetail.controls as any)?.theme || 'corporate_blue'}
                  selectedIndex={activeSlideIndex}
                  onSelectSlide={selectSlideForEdit}
                />

                <div className="flex overflow-x-auto gap-2 py-2">
                  <button
                    onClick={() => selectSlideForEdit(0)}
                    className={`flex h-14 w-24 shrink-0 flex-col items-center justify-center rounded-lg border text-[10px] font-bold transition ${
                      activeSlideIndex === 0
                        ? 'border-brand-600 bg-blue-50 text-brand-600 ring-2 ring-brand-400'
                        : 'border-ink-200 bg-white text-ink-600 hover:border-ink-400'
                    }`}
                  >
                    <span>Slide 1</span>
                    <span className="truncate max-w-[80px] text-[9px] font-normal">Title Slide</span>
                  </button>
                  {outputDetail.content_ir.nodes
                    .filter((n) => n.kind === 'slide')
                    .map((node, i) => (
                      <button
                        key={node.id}
                        onClick={() => selectSlideForEdit(i + 1)}
                        className={`flex h-14 w-24 shrink-0 flex-col items-center justify-center rounded-lg border p-1 text-[10px] font-bold transition ${
                          activeSlideIndex === i + 1
                            ? 'border-brand-600 bg-blue-50 text-brand-600 ring-2 ring-brand-400'
                            : 'border-ink-200 bg-white text-ink-600 hover:border-ink-400'
                        }`}
                      >
                        <span>Slide {i + 2}</span>
                        <span className="truncate max-w-[80px] text-[9px] font-normal">
                          {node.title || 'Untitled'}
                        </span>
                      </button>
                    ))}
                </div>
              </div>

              {/* Side Quick Edit Teaser */}
              <div className="space-y-4 rounded-xl border border-ink-200 bg-white p-4 shadow-xs">
                <h3 className="text-sm font-bold text-ink-900 border-b border-ink-100 pb-2">
                  Quick Actions
                </h3>
                <p className="text-xs text-ink-500">
                  Open the full Presentation Editor to customize titles, layout types, bullet content, themes, and slide counts.
                </p>
                <Button wide onClick={handleOpenEditWorkspace}>
                  <Icon name="edit" />
                  Open Presentation Editor
                </Button>
                {userModifiedCount > 0 && (
                  <p className="text-[11px] text-amber-700 font-semibold bg-amber-50 p-2 rounded border border-amber-200">
                    {userModifiedCount} slide(s) manually customized.
                  </p>
                )}
              </div>
            </div>
          )}

          {/* CONFIRMATION / SCOPE MODAL FOR RECONFIGURATION */}
          {showReconfigModal && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
              <div className="w-full max-w-md space-y-4 rounded-2xl bg-white p-6 shadow-xl border border-ink-200">
                <h3 className="text-base font-bold text-ink-900 flex items-center gap-2">
                  <Icon name="spark" className="text-brand-600" />
                  Regenerate Presentation Content
                </h3>

                <p className="text-xs text-ink-600">
                  Apply updated purpose, audience, language, or detail level settings to your presentation.
                </p>

                <Field label="Scope of Regeneration">
                  <Segmented
                    options={[
                      { key: 'all', label: 'Apply to All Slides' },
                      { key: 'selected', label: 'Apply to Selected Slides' },
                    ]}
                    value={reconfigScope}
                    onChange={(v) => setReconfigScope(v as any)}
                  />
                </Field>

                {reconfigScope === 'selected' && outputDetail && (
                  <div className="max-h-40 overflow-y-auto space-y-1 rounded-lg border border-ink-200 p-2 text-xs">
                    {outputDetail.content_ir.nodes
                      .filter((n) => n.kind === 'slide')
                      .map((s, idx) => (
                        <label key={s.id} className="flex items-center gap-2 py-1 px-1 hover:bg-ink-50 rounded cursor-pointer">
                          <input
                            type="checkbox"
                            checked={selectedSlideIdsForRegen.includes(s.id)}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setSelectedSlideIdsForRegen([...selectedSlideIdsForRegen, s.id])
                              } else {
                                setSelectedSlideIdsForRegen(selectedSlideIdsForRegen.filter((id) => id !== s.id))
                              }
                            }}
                            className="rounded border-ink-300 text-brand-600"
                          />
                          <span>#{idx + 1}: {s.title}</span>
                        </label>
                      ))}
                  </div>
                )}

                {userModifiedCount > 0 && (
                  <label className="flex items-center gap-2 rounded-lg bg-amber-50 p-2.5 text-xs text-amber-900 border border-amber-200">
                    <input
                      type="checkbox"
                      checked={preserveUserEdits}
                      onChange={(e) => setPreserveUserEdits(e.target.checked)}
                      className="rounded border-amber-400 text-amber-600"
                    />
                    <span>Preserve {userModifiedCount} manually edited slide(s)</span>
                  </label>
                )}

                <div className="flex items-center justify-end gap-2 pt-2 border-t border-ink-100">
                  <Button variant="ghost" onClick={() => setShowReconfigModal(false)}>
                    Cancel
                  </Button>
                  <Button onClick={handleReconfigureContent} disabled={reconfiguring}>
                    {reconfiguring ? 'Regenerating…' : 'Confirm & Regenerate'}
                  </Button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
