import { Link } from 'react-router-dom'
import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { formatDate, toSentenceCase } from '../utils/formatters'

function formatEstimate(minutes) {
  if (!minutes) return null
  if (minutes < 60) return `${minutes} min`
  const hours = minutes / 60
  return Number.isInteger(hours) ? `${hours} hr` : `${hours.toFixed(1)} hr`
}

export default function TaskCard({ task, isDragging = false }) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id: task.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  const priorityTone = {
    critical: 'from-rose-500 to-orange-500',
    high: 'from-orange-400 to-amber-500',
    medium: 'from-emerald-500 to-teal-500',
    low: 'from-slate-400 to-slate-500',
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className={`glass-panel cursor-grab p-4 transition-all duration-300 ${isDragging ? 'scale-[1.01] opacity-95 shadow-glow' : 'hover:-translate-y-0.5'}`}
    >
      <Link to={`/tasks/${task.id}`} className="block">
        <div className="flex items-center justify-between gap-3">
          <div className={`h-1.5 w-16 rounded-full bg-gradient-to-r ${priorityTone[task.priority] || priorityTone.low}`} />
          <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">
            {task.status?.replaceAll('_', ' ')}
          </span>
        </div>
        <h4 className="mt-4 text-base font-bold text-slate-950">{task.title}</h4>
        {task.description ? <p className="mt-2 text-sm text-soft line-clamp-2">{task.description}</p> : null}
      </Link>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <span className="stat-chip">{toSentenceCase(task.priority)}</span>
        {task.recurrence_pattern && task.recurrence_pattern !== 'none' ? (
          <span className="micro-chip">{toSentenceCase(task.recurrence_pattern)}</span>
        ) : null}
        {task.blocked_reason ? (
          <span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-700">Blocked</span>
        ) : null}
        {task.is_overdue ? <span className="rounded-full bg-rose-50 px-3 py-1 text-xs font-semibold text-rose-700">Overdue</span> : null}
      </div>

      <div className="mt-3 flex flex-wrap gap-3 text-xs font-medium text-soft">
        {formatEstimate(task.estimated_minutes) ? <span>{formatEstimate(task.estimated_minutes)}</span> : null}
        {task.planned_for_date ? <span>Planned {formatDate(task.planned_for_date)}</span> : null}
      </div>

      <p className="mt-4 text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
        Due {formatDate(task.due_date)}
      </p>
    </div>
  )
}
