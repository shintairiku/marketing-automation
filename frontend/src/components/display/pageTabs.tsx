

// export type TabOption = {
//     label: string
//     value: string
//   }

// type PageTabsProps = {
//   options: TabOption[]
//   value: string
//   onChange: (value: string) => void
// }

// export default function PageTabs({ options, value, onChange }: PageTabsProps) {
//   const selectedIdx = options.findIndex(opt => opt.value === value)

//   return (
//     <div className="relative flex bg-[#f9f9f9] rounded-full p-1">
//       {/* 選択中の背景 */}
//       <div
//         className="absolute top-0 left-0 h-full rounded-full bg-white transition-all duration-300"
//         style={{
//           width: `calc(100% / ${options.length})`,
//           transform: `translateX(${selectedIdx * 100}%)`,
//           zIndex: 1,
//         }}
//       >
//         <div className="w-full h-full rounded-full shadow" />
//       </div>
//       {options.map((opt, idx) => (
//         <button
//           key={opt.value}
//           className={`flex-1 min-w-[200px] relative z-10 py-2 text-base rounded-full transition-colors duration-300 ${
//             value === opt.value ? "text-[#E5581C] font-bold" : "text-gray-400"
//           }`}
//           onClick={() => onChange(opt.value)}
//         >
//           {opt.label}
//         </button>
//       ))}
//     </div>
//   )
// }