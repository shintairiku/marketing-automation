import ExplainDialog from "./ExplainDialog";
import InputSection from "./InputSection";
import AiThinkingBox from "../component/AiThinkingBox";
import GeneratedTitleSection from "./GeneratedTitleSection";
import GeneratedOutlineSection from "./GeneratedOutlineSection";
import GeneratedBodySection from "./GeneratedBodySection";
export default function IndexPage() {
    return (
        <div className="w-full max-w-6xl mx-auto">
            <ExplainDialog />
            <InputSection />
            <AiThinkingBox />
            <GeneratedTitleSection />
            <AiThinkingBox />
            <GeneratedOutlineSection />
            <AiThinkingBox />
            <GeneratedBodySection />
        </div>
    )
}