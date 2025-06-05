import AiThinkingBox from "../component/AiThinkingBox";

import ExplainDialog from "./ExplainDialog";
import GeneratedBodySection from "./GeneratedBodySection";
import GeneratedOutlineSection from "./GeneratedOutlineSection";
import GeneratedTitleSection from "./GeneratedTitleSection";
import InputSection from "./InputSection";
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