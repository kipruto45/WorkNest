import { Link } from 'react-router-dom'
import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { formatDate, toSentenceCase } from '../utils/formatters'

export default function TaskCard({ task, isDragging = false }) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id: task.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  const priorityTone = {
    critical: 'from-rose-500 to-orange-500',
    high: 'from-orange-400 to-amber-500',
    medium: 'from-lime-400 to-emerald-500',
    low: 'from-slate-400 to-slate-500',
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className={`glass-panel cursor-grab p-4 transition-all duration-300 ${isDragging ? 'scale-[1.02] opacity-90 shadow-glow' : 'hover:-translate-y-1'}`}
    >
      <Link to={`/tasks/${task.id}`} className="block">
        <div className={`h-1.5 w-20 rounded-full bg-gradient-to-r ${priorityTone[task.priority] || priorityTone.low}`} />
        <h4 className="mt-4 text-base font-bold text-emerald-950">{task.title}</h4>
        {task.description ? <p className="mt-2 text-sm text-soft line-clamp-2">{task.description}</p> : null}
      </Link>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <span className="stat-chip">{toSentenceCase(task.priority)}</span>
        {task.is_overdue ? <span className="rounded-full bg-rose-100 px-3 py-1 text-xs font-semibold text-rose-700">Overdue</span> : null}
      </div>

      <p className="mt-4 text-xs font-semibold uppercase tracking-[0.16em] text-soft">
        Due {formatDate(task.due_date)}
      </p>
    </div>
  )
}
