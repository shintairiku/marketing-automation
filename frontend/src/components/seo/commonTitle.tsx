export default function CommonTitle({ title }: { title: string }) {
    return (
        <div className="flex gap-5 items-center">
            <div className="w-2 h-8 bg-pink-100"></div>
            <h1 className="text-base font-bold">{title}</h1>
        </div>
    )
}