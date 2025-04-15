import { cn } from '@/utils/cn';

export function Logo({ className }: { className?: string }) {
  return (
    <div className={cn('flex items-center gap-2', className)}>
      <span className='font-alt text-xl text-white'>新大陸</span>
    </div>
  );
}
