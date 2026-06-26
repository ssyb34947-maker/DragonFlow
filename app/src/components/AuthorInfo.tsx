import { UserRound } from 'lucide-react'

const authorNames = ['沈昱兵', '黄俊尧', '马祺喆']

type AuthorInfoProps = {
  className?: string
}

export default function AuthorInfo({ className = '' }: AuthorInfoProps) {
  return (
    <div className={`rounded-lg border border-primary/25 bg-primary/[0.055] p-4 ${className}`}>
      <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-fg">
        <UserRound className="h-4 w-4 text-primary" />
        作者信息
      </div>
      <div className="flex flex-wrap gap-2">
        {authorNames.map((name, index) => (
          <span
            key={`${name}-${index}`}
            className="rounded-md border border-border bg-black/20 px-3 py-1.5 text-sm font-medium text-fg"
          >
            {name}
          </span>
        ))}
      </div>
    </div>
  )
}
