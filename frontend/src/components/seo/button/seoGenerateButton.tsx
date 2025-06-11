
export default function SeoGenerateButton({generateButtonText}: {generateButtonText: string}) {
    return (
        <button className="bg-pink-100 font-bold text-black px-4 py-2 rounded-full">
            {generateButtonText}
        </button>
    )
}