interface SeoNextButtonProps {
    nextButtonText: string;
    onClick: () => void;
}

export default function SeoNextButton({ nextButtonText, onClick }: SeoNextButtonProps) {
    return (
        <button 
            onClick={onClick}
            className="bg-pink-100 text-black px-4 py-2 rounded-full"
        >
            Next.../{nextButtonText}
        </button>
    )
}