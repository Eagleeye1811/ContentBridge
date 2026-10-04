import DeckPreview from '@/components/preview/DeckPreview'
import DocumentPreview from '@/components/preview/DocumentPreview'
import EmailPreview from '@/components/preview/EmailPreview'
import InfographicPreview from '@/components/preview/InfographicPreview'
import LinkedInPreview from '@/components/preview/LinkedInPreview'
import PressReleasePreview from '@/components/preview/PressReleasePreview'
import TwitterPreview from '@/components/preview/TwitterPreview'
import VideoPreview from '@/components/preview/VideoPreview'
import type { ContentIR, Fact } from '@/types/api'

const AUDIENCE: Record<string, string> = {
  officer: 'Staff',
  management: 'Senior officials',
  technical: 'Technical team',
  public: 'Citizens',
  social: 'Followers',
}

/** Each output type previewed the way it will actually be used. */
export default function OutputPreview({
  type,
  ir,
  audience,
  options = {},
  outputId,
  facts,
}: {
  type: string
  ir: ContentIR
  audience: string
  options?: Record<string, string>
  outputId?: string
  facts?: Fact[]
}) {
  switch (type) {
    case 'ppt':
      return <DeckPreview ir={ir} />
    case 'email':
      return (
        <EmailPreview
          ir={ir}
          audience={AUDIENCE[audience] ?? audience}
          outputId={outputId}
          options={options}
        />
      )
    case 'press_release':
      return <PressReleasePreview ir={ir} />
    case 'linkedin':
    case 'social':
      return <LinkedInPreview ir={ir} />
    case 'twitter':
      return <TwitterPreview ir={ir} />
    case 'infographic':
      return <InfographicPreview ir={ir} shape={options.shape} />
    case 'video':
      return <VideoPreview ir={ir} screen={options.screen} outputId={outputId} />
    case 'advisory':
      return <DocumentPreview ir={ir} kicker="Advisory" facts={facts} />
    case 'summary':
      return <DocumentPreview ir={ir} kicker="Executive summary" facts={facts} />
    case 'report':
      return <DocumentPreview ir={ir} kicker="Report" facts={facts} />
    default:
      return <DocumentPreview ir={ir} kicker="" facts={facts} />
  }
}
