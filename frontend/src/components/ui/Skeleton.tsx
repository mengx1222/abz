import { cn } from '../../utils/cn';

interface SkeletonProps {
  className?: string;
}

/** 骨架屏基础块：配合 Tailwind animate-pulse 组合出加载占位 */
export function Skeleton({ className }: SkeletonProps) {
  return <div aria-hidden="true" className={cn('animate-pulse rounded-md bg-border/60', className)} />;
}
