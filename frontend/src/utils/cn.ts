import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

/** 合并 class 名：clsx 处理条件拼接，twMerge 消解 Tailwind 冲突（后者覆盖前者） */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
