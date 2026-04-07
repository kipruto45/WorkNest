import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import AppLogo from '../components/AppLogo'

const navItems = [
  { label: 'Features', href: '#features' },
  { label: 'Teams', href: '#teams' },
  { label: 'Tasks', href: '#workflow' },
  { label: 'Demo', href: '#demo' },
  { label: 'Contact', to: '/contact' },
]

const trustMetrics = [
  { value: '2,400+', label: 'teams running daily work in WorkNest' },
  { value: '480k+', label: 'tasks planned and completed each month' },
  { value: '99.9%', label: 'platform uptime for active workspaces' },
  { value: '<2 min', label: 'average time to create and assign work' },
]

const features = [
  {
    title: 'Create and assign work clearly',
    description: 'Capture tasks in seconds, assign owners, set due dates, and keep scope visible from the start.',
    icon: PlusIcon,
  },
  {
    title: 'Track priorities and deadlines',
    description: 'Separate what is urgent from what is important with clear due dates, statuses, and priority markers.',
    icon: CalendarIcon,
  },
  {
    title: 'Collaborate where the work lives',
    description: 'Use comments, mentions, and task history so conversations stay attached to the exact item being discussed.',
    icon: ChatIcon,
  },
  {
    title: 'Stay aligned with notifications',
    description: 'Assignments, mentions, and deadline reminders surface in one clean activity stream.',
    icon: BellIcon,
  },
  {
    title: 'Give teams the right level of control',
    description: 'Manage workspace roles, member access, invitations, and visibility without extra admin overhead.',
    icon: ShieldIcon,
  },
  {
    title: 'Measure progress with clarity',
    description: 'Review workload, overdue items, completed work, and delivery trends from a focused dashboard.',
    icon: ChartIcon,
  },
]

const workflowSteps = [
  {
    number: '01',
    title: 'Create work',
    description: 'Add tasks with clear scope, due dates, priority, and ownership before work gets lost in chat.',
  },
  {
    number: '02',
    title: 'Collaborate in context',
    description: 'Discuss tasks, mention teammates, and update statuses directly inside the workspace.',
  },
  {
    number: '03',
    title: 'Track progress in real time',
    description: 'Use boards, summaries, and activity views to see what is moving, blocked, or overdue.',
  },
]

const footerColumns = [
  {
    title: 'Product',
    links: [
      { label: 'Features', href: '#features' },
      { label: 'Task Boards', href: '#workflow' },
      { label: 'Notifications', href: '#demo' },
      { label: 'Dashboards', href: '#demo' },
    ],
  },
  {
    title: 'Company',
    links: [
      { label: 'About', to: '/about' },
      { label: 'Demo', href: '#demo' },
      { label: 'Contact', to: '/contact' },
      { label: 'Support', to: '/support' },
    ],
  },
  {
    title: 'Resources',
    links: [
      { label: 'Help Center', to: '/help-center' },
      { label: 'API Docs', to: '/api-docs' },
      { label: 'Status', to: '/status' },
      { label: 'Security', to: '/security' },
    ],
  },
]

const primaryButtonClass =
  'inline-flex items-center justify-center rounded-xl bg-emerald-600 px-5 py-3 text-sm font-semibold text-white transition-colors duration-200 hover:bg-emerald-700'

const secondaryButtonClass =
  'inline-flex items-center justify-center rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-900 transition-colors duration-200 hover:border-slate-400 hover:bg-slate-50'

const sectionClass = 'mx-auto max-w-7xl px-4 sm:px-6 lg:px-8'
const surfaceClass = 'rounded-3xl border border-slate-200 bg-white shadow-[0_12px_36px_rgba(15,23,42,0.06)]'

export default function Landing() {
  const [isScrolled, setIsScrolled] = useState(false)

  useEffect(() => {
    const onScroll = () => setIsScrolled(window.scrollY > 12)

    onScroll()
    window.addEventListener('scroll', onScroll)

    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <div className="min-h-screen bg-[#fafaf8] text-slate-950">
      <header
        className={`sticky top-0 z-40 border-b transition-all duration-300 ${
          isScrolled
            ? 'border-slate-200/80 bg-[rgba(250,250,248,0.92)] backdrop-blur-xl'
            : 'border-transparent bg-transparent'
        }`}
      >
        <div className={`${sectionClass}`}>
          <div className="flex h-20 items-center justify-between">
            <AppLogo
              to="/"
              subtitle="Task management for focused teams"
              imageClassName="h-11 w-11"
              titleClassName="text-sm font-semibold uppercase tracking-[0.22em] text-emerald-700"
              subtitleClassName="text-sm text-slate-500"
            />

            <nav className="hidden items-center gap-8 lg:flex">
              {navItems.map((item) =>
                item.to ? (
                  <Link
                    key={item.label}
                    to={item.to}
                    className="text-sm font-medium text-slate-600 transition-colors hover:text-slate-950"
                  >
                    {item.label}
                  </Link>
                ) : (
                  <a
                    key={item.href}
                    href={item.href}
                    className="text-sm font-medium text-slate-600 transition-colors hover:text-slate-950"
                  >
                    {item.label}
                  </a>
                )
              )}
            </nav>

            <div className="flex items-center gap-3">
              <Link to="/login" className="hidden text-sm font-semibold text-slate-700 transition-colors hover:text-slate-950 sm:inline-flex">
                Sign In
              </Link>
              <Link to="/register" className={primaryButtonClass}>
                Get Started
              </Link>
            </div>
          </div>
        </div>
      </header>

      <main>
        <section className={`${sectionClass} pb-20 pt-10 md:pb-24 md:pt-16`}>
          <div className="grid items-center gap-14 lg:grid-cols-[0.9fr,1.1fr] xl:grid-cols-[0.86fr,1.14fr]">
            <div className="fade-in">
              <div className="inline-flex items-center rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">
                Built for modern product, operations, and delivery teams
              </div>
              <h1 className="mt-6 max-w-3xl text-balance font-display text-5xl font-bold tracking-tight text-slate-950 md:text-6xl">
                Organize work. Align teams. Deliver faster.
              </h1>
              <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-600">
                WorkNest gives teams a cleaner way to plan tasks, assign ownership, track deadlines, and stay in sync
                without relying on scattered tools or noisy workflows.
              </p>

              <div className="mt-8 flex flex-wrap gap-3">
                <Link to="/register" className={primaryButtonClass}>
                  Get Started
                </Link>
                <a href="#workflow" className={secondaryButtonClass}>
                  View Workflow
                </a>
              </div>

              <div className="mt-6 flex flex-wrap items-center gap-x-6 gap-y-3 text-sm text-slate-500">
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-emerald-500" />
                  No setup friction
                </div>
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-emerald-500" />
                  Role-based team workspaces
                </div>
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-emerald-500" />
                  Real-time visibility
                </div>
              </div>
            </div>

            <div className="fade-in-delayed">
              <HeroProductPreview surfaceClass={surfaceClass} />
            </div>
          </div>
        </section>

        <section className="border-y border-slate-200 bg-white">
          <div className={`${sectionClass} py-8`}>
            <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
              {trustMetrics.map((metric) => (
                <div key={metric.label} className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-2xl font-bold tracking-tight text-slate-950">{metric.value}</p>
                    <p className="mt-2 max-w-[20ch] text-sm leading-6 text-slate-600">{metric.label}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="features" className={`${sectionClass} scroll-mt-28 py-20 md:py-24`}>
          <SectionHeading
            eyebrow="Features"
            title="Everything teams need to keep work structured and visible"
            description="WorkNest focuses on the essentials that make team execution smoother: clear ownership, dependable deadlines, collaboration in context, and cleaner progress tracking."
          />

          <div className="mt-12 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
            {features.map((feature) => {
              const Icon = feature.icon
              return (
                <article
                  key={feature.title}
                  className="fade-in rounded-[28px] border border-slate-200 bg-white p-6 shadow-[0_10px_30px_rgba(15,23,42,0.04)] transition-transform duration-200 hover:-translate-y-1"
                >
                  <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-700">
                    <Icon className="h-5 w-5" />
                  </div>
                  <h3 className="mt-5 text-xl font-semibold text-slate-950">{feature.title}</h3>
                  <p className="mt-3 text-sm leading-7 text-slate-600">{feature.description}</p>
                </article>
              )
            })}
          </div>
        </section>

        <section id="workflow" className="border-y border-slate-200 bg-white">
          <div className={`${sectionClass} scroll-mt-28 py-20 md:py-24`}>
            <div className="grid items-start gap-14 lg:grid-cols-[0.9fr,1.1fr]">
              <div className="fade-in">
                <SectionHeading
                  eyebrow="Workflow"
                  title="A product-led workflow that matches how teams actually operate"
                  description="The workflow is simple on purpose: create work clearly, collaborate inside the task, and keep progress visible across the whole team."
                  align="left"
                />

                <div className="mt-10 space-y-5">
                  {workflowSteps.map((step) => (
                    <div key={step.number} className="flex gap-4 rounded-3xl border border-slate-200 bg-[#fcfcfb] p-5">
                      <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-slate-900 text-sm font-semibold text-white">
                        {step.number}
                      </div>
                      <div>
                        <h3 className="text-lg font-semibold text-slate-950">{step.title}</h3>
                        <p className="mt-2 text-sm leading-7 text-slate-600">{step.description}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="fade-in-delayed">
                <WorkflowPreview surfaceClass={surfaceClass} />
              </div>
            </div>
          </div>
        </section>

        <section id="teams" className={`${sectionClass} scroll-mt-28 py-20 md:py-24`}>
          <div className="grid items-center gap-14 lg:grid-cols-[1.02fr,0.98fr]">
            <div className="fade-in">
              <TeamCollaborationPreview surfaceClass={surfaceClass} />
            </div>

            <div className="fade-in-delayed">
              <SectionHeading
                eyebrow="Team Collaboration"
                title="Built for teams that need clarity, not noise"
                description="Assign responsibilities, comment in context, mention teammates, manage invites, and keep roles organized without breaking flow."
                align="left"
              />

              <div className="mt-8 space-y-4">
                {[
                  'Assign work to the right owner without ambiguity.',
                  'Keep updates, decisions, and mentions attached to each task.',
                  'Manage invitations and roles from the same workspace.',
                  'Give every teammate a clearer view of what is moving and what needs attention.',
                ].map((item) => (
                  <div key={item} className="flex gap-3 text-sm leading-7 text-slate-600">
                    <span className="mt-2 h-2.5 w-2.5 rounded-full bg-emerald-600" />
                    <span>{item}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section id="demo" className="border-y border-slate-200 bg-white">
          <div className={`${sectionClass} scroll-mt-28 py-20 md:py-24`}>
            <div className="grid items-center gap-14 lg:grid-cols-[0.92fr,1.08fr]">
              <div className="fade-in">
                <SectionHeading
                  eyebrow="Dashboards & Analytics"
                  title="A cleaner way to see workload, deadlines, and delivery health"
                  description="Track overdue items, completed work, active projects, and team progress from a dashboard that stays readable under real use."
                  align="left"
                />

                <div className="mt-8 grid gap-4 sm:grid-cols-2">
                  <MiniMetric title="Overdue tasks" value="12" />
                  <MiniMetric title="Completed this week" value="184" />
                  <MiniMetric title="Active projects" value="28" />
                  <MiniMetric title="Team progress" value="76%" />
                </div>
              </div>

              <div className="fade-in-delayed">
                <AnalyticsPreview surfaceClass={surfaceClass} />
              </div>
            </div>
          </div>
        </section>

        <section className={`${sectionClass} py-20 md:py-24`}>
          <div className="rounded-[36px] border border-slate-200 bg-slate-950 px-6 py-10 text-white shadow-[0_16px_50px_rgba(2,6,23,0.16)] md:px-10 md:py-12">
            <div className="grid gap-8 lg:grid-cols-[1.1fr,0.9fr] lg:items-center">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.18em] text-emerald-300">Start with a cleaner workflow</p>
                <h2 className="mt-4 max-w-2xl text-balance font-display text-4xl font-bold tracking-tight">
                  Give your team a modern workspace for tasks, deadlines, and collaboration.
                </h2>
                <p className="mt-4 max-w-2xl text-base leading-7 text-slate-300">
                  WorkNest helps teams move from planning to delivery with better visibility, clearer ownership, and less operational noise.
                </p>
              </div>

              <div className="flex flex-wrap gap-3 lg:justify-end">
                <Link to="/register" className="inline-flex items-center justify-center rounded-xl bg-emerald-500 px-5 py-3 text-sm font-semibold text-slate-950 transition-colors hover:bg-emerald-400">
                  Get Started
                </Link>
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer id="contact" className="border-t border-slate-200 bg-white">
        <div className={`${sectionClass} py-14`}>
          <div className="grid gap-10 lg:grid-cols-[1.15fr,0.85fr]">
            <div>
              <AppLogo
                subtitle="Task management & team collaboration"
                imageClassName="h-11 w-11"
                titleClassName="text-sm font-semibold uppercase tracking-[0.22em] text-emerald-700"
                subtitleClassName="text-sm text-slate-500"
              />
              <p className="mt-5 max-w-md text-sm leading-7 text-slate-600">
                A refined workspace for teams that need structure, visibility, and a more dependable way to manage work together.
              </p>
              <div className="mt-6 flex flex-wrap gap-4 text-sm font-medium text-slate-500">
                <a href="mailto:kiprutovictor39@gmail.com" className="transition-colors hover:text-slate-950">
                  kiprutovictor39@gmail.com
                </a>
                <Link to="/status" className="transition-colors hover:text-slate-950">
                  Status
                </Link>
                <Link to="/security" className="transition-colors hover:text-slate-950">
                  Security
                </Link>
              </div>
            </div>

            <div className="grid gap-8 sm:grid-cols-3">
              {footerColumns.map((column) => (
                <div key={column.title}>
                  <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-950">{column.title}</h3>
                  <div className="mt-4 space-y-3">
                    {column.links.map((link) =>
                      link.to ? (
                        <Link key={link.label} to={link.to} className="block text-sm text-slate-600 transition-colors hover:text-slate-950">
                          {link.label}
                        </Link>
                      ) : (
                        <a key={link.label} href={link.href} className="block text-sm text-slate-600 transition-colors hover:text-slate-950">
                          {link.label}
                        </a>
                      )
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-12 flex flex-col gap-3 border-t border-slate-200 pt-6 text-sm text-slate-500 sm:flex-row sm:items-center sm:justify-between">
            <p>© 2026 WorkNest. All rights reserved.</p>
            <div className="flex items-center gap-5">
              <Link to="/about" className="transition-colors hover:text-slate-950">
                About
              </Link>
              <Link to="/support" className="transition-colors hover:text-slate-950">
                Support
              </Link>
              <a
                href="https://github.com/kipruto45"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-2 transition-colors hover:text-slate-950"
                aria-label="WorkNest GitHub"
              >
                <GitHubIcon className="h-5 w-5" />
                <span>GitHub</span>
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}

function SectionHeading({ eyebrow, title, description, align = 'center' }) {
  const alignment = align === 'left' ? 'text-left' : 'mx-auto max-w-3xl text-center'

  return (
    <div className={alignment}>
      <p className="text-sm font-semibold uppercase tracking-[0.18em] text-emerald-700">{eyebrow}</p>
      <h2 className="mt-4 text-balance font-display text-4xl font-bold tracking-tight text-slate-950">{title}</h2>
      <p className="mt-4 text-base leading-8 text-slate-600">{description}</p>
    </div>
  )
}

function MiniMetric({ title, value }) {
  return (
    <div className="rounded-[24px] border border-slate-200 bg-[#fcfcfb] p-5">
      <p className="text-sm text-slate-500">{title}</p>
      <p className="mt-3 text-3xl font-bold tracking-tight text-slate-950">{value}</p>
    </div>
  )
}

function HeroProductPreview({ surfaceClass }) {
  return (
    <div className={`${surfaceClass} mx-auto w-full max-w-[820px] overflow-hidden bg-[#f4f5f3] xl:max-w-[920px]`}>
      <div className="flex items-center justify-between border-b border-slate-200 bg-[#eef1ee] px-4 py-3.5">
        <div className="flex items-center gap-2.5">
          <span className="h-3 w-3 rounded-full bg-[#ff5f57]" />
          <span className="h-3 w-3 rounded-full bg-[#febc2e]" />
          <span className="h-3 w-3 rounded-full bg-[#28c840]" />
        </div>
        <div className="flex min-w-0 items-center gap-3">
          <div className="hidden rounded-full border border-slate-200 bg-white px-3 py-1.5 text-[11px] font-medium text-slate-500 sm:block">
            worknest.app/workspace
          </div>
          <div className="text-xs font-medium uppercase tracking-[0.16em] text-slate-500">WorkNest Workspace</div>
        </div>
      </div>

      <div className="border-b border-slate-200 bg-white/80 px-4 py-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-full bg-slate-900 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-white">
            Team board
          </span>
          <span className="rounded-full bg-slate-100 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-600">
            Sprint 12
          </span>
          <span className="rounded-full bg-emerald-50 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-emerald-700">
            Live workspace
          </span>
        </div>
      </div>

      <div className="grid gap-4 p-4 lg:grid-cols-[170px,1fr]">
        <aside className="rounded-[20px] border border-white/80 bg-[#eef2ef] p-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.7)]">
          <div className="rounded-2xl bg-white p-3">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Overview</p>
            <p className="mt-2 text-2xl font-bold tracking-tight text-slate-950">184</p>
            <p className="mt-1 text-sm text-slate-500">tasks in progress</p>
          </div>
          <div className="mt-3 space-y-2">
            <SidebarItem label="Team Board" active />
            <SidebarItem label="My Tasks" />
            <SidebarItem label="Notifications" />
            <SidebarItem label="Reports" />
          </div>
        </aside>

        <div>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            <StatusColumn
              title="To do"
              count="16"
              items={[
                ['Onboarding refresh', 'High priority'],
                ['Client handoff notes', 'Due tomorrow'],
              ]}
            />
            <StatusColumn
              title="In progress"
              count="09"
              items={[
                ['Mobile QA review', 'Assigned to Maya'],
                ['Pricing updates', 'In review'],
              ]}
            />
            <StatusColumn
              title="Done"
              count="24"
              items={[
                ['Weekly planning', 'Completed'],
                ['Dashboard cleanup', 'Closed'],
              ]}
            />
          </div>

          <div className="mt-4 rounded-[20px] border border-slate-200 bg-[#fcfcfb] p-3.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.7)]">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-sm font-semibold text-slate-950">Upcoming deadlines</p>
                <p className="mt-1 text-sm text-slate-500">A cleaner view of what needs attention this week.</p>
              </div>
              <div className="text-sm font-medium text-emerald-700">View calendar</div>
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <DeadlineRow name="Customer launch checklist" date="Today" />
              <DeadlineRow name="Design QA handoff" date="Thu" />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function WorkflowPreview({ surfaceClass }) {
  return (
    <div className={`${surfaceClass} overflow-hidden`}>
      <div className="border-b border-slate-200 px-6 py-5">
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-emerald-700">Product workflow</p>
        <h3 className="mt-2 text-2xl font-semibold text-slate-950">Create, discuss, and move work forward</h3>
      </div>
      <div className="space-y-4 p-6">
        <div className="rounded-[24px] border border-slate-200 bg-[#fcfcfb] p-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">New task</p>
              <h4 className="mt-2 text-lg font-semibold text-slate-950">Launch account migration</h4>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                Owner, due date, and delivery scope are clear before work begins.
              </p>
            </div>
            <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">
              Assigned
            </span>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-[1.1fr,0.9fr]">
          <div className="rounded-[24px] border border-slate-200 bg-white p-4">
            <p className="text-sm font-semibold text-slate-950">Contextual discussion</p>
            <div className="mt-4 space-y-4">
              <CommentBubble author="Maya" message="The updated flow is ready for review. I’ve tagged design for sign-off." />
              <CommentBubble author="Noah" message="Looks good. I’ll confirm the deadline and move it into review." muted />
            </div>
          </div>

          <div className="rounded-[24px] border border-slate-200 bg-[#f6f8f7] p-4">
            <p className="text-sm font-semibold text-slate-950">Live status</p>
            <div className="mt-4 space-y-3">
              <ProgressRow label="Planning" value="100%" />
              <ProgressRow label="Execution" value="76%" />
              <ProgressRow label="Review" value="42%" />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function TeamCollaborationPreview({ surfaceClass }) {
  return (
    <div className={`${surfaceClass} overflow-hidden`}>
      <div className="grid gap-4 p-6">
        <div className="rounded-[28px] border border-slate-200 bg-[#fcfcfb] p-5">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Shared workspace</p>
              <h3 className="mt-2 text-2xl font-semibold text-slate-950">Delivery team</h3>
            </div>
            <AvatarGroup />
          </div>
          <div className="mt-5 grid gap-3 sm:grid-cols-3">
            <SimpleStat label="Members" value="14" />
            <SimpleStat label="Open tasks" value="38" />
            <SimpleStat label="Invites pending" value="3" />
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-[0.92fr,1.08fr]">
          <div className="rounded-[24px] border border-slate-200 bg-white p-5">
            <p className="text-sm font-semibold text-slate-950">Team roles</p>
            <div className="mt-4 space-y-3">
              <MemberRow name="Amina J." role="Admin" />
              <MemberRow name="Maya K." role="Manager" />
              <MemberRow name="Noah T." role="Member" />
            </div>
          </div>

          <div className="rounded-[24px] border border-slate-200 bg-white p-5">
            <p className="text-sm font-semibold text-slate-950">Activity and mentions</p>
            <div className="mt-4 space-y-4">
              <NotificationRow title="Mentioned in launch checklist" time="2 min ago" />
              <NotificationRow title="Task assigned: Mobile QA review" time="9 min ago" />
              <NotificationRow title="Invitation accepted by Alex" time="18 min ago" />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function AnalyticsPreview({ surfaceClass }) {
  return (
    <div className={`${surfaceClass} overflow-hidden`}>
      <div className="grid gap-4 p-6">
        <div className="grid gap-4 sm:grid-cols-3">
          <MetricCard title="Completed" value="184" />
          <MetricCard title="Overdue" value="12" />
          <MetricCard title="Active teams" value="9" />
        </div>

        <div className="grid gap-4 md:grid-cols-[1fr,320px]">
          <div className="rounded-[24px] border border-slate-200 bg-white p-5">
            <div className="flex items-center justify-between">
              <p className="text-sm font-semibold text-slate-950">Weekly progress</p>
              <p className="text-sm text-slate-500">Last 7 days</p>
            </div>
            <div className="mt-6 flex h-56 items-end gap-3">
              {[44, 56, 72, 60, 84, 68, 92].map((height, index) => (
                <div key={height} className="flex flex-1 flex-col items-center gap-3">
                  <div
                    className={`w-full rounded-t-2xl ${index === 6 ? 'bg-emerald-600' : 'bg-slate-200'}`}
                    style={{ height: `${height * 1.6}px` }}
                  />
                  <span className="text-xs font-medium text-slate-500">
                    {['M', 'T', 'W', 'T', 'F', 'S', 'S'][index]}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-[24px] border border-slate-200 bg-[#fcfcfb] p-5">
            <p className="text-sm font-semibold text-slate-950">Deadline calendar</p>
            <div className="mt-4 space-y-3">
              <CalendarEvent day="14" month="May" title="Client review" />
              <CalendarEvent day="16" month="May" title="Launch prep" />
              <CalendarEvent day="20" month="May" title="Quarterly planning" />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function SidebarItem({ label, active = false }) {
  return (
    <div
      className={`flex items-center justify-between rounded-2xl px-4 py-3 text-sm font-medium ${
        active ? 'bg-emerald-600 text-white' : 'bg-white text-slate-600'
      }`}
    >
      <span>{label}</span>
      <span className={`h-2 w-2 rounded-full ${active ? 'bg-white' : 'bg-slate-300'}`} />
    </div>
  )
}

function StatusColumn({ title, count, items }) {
  return (
    <div className="rounded-[22px] border border-slate-200 bg-[#fcfcfb] p-4">
      <div className="flex items-start justify-between gap-3">
        <p className="text-base font-semibold leading-6 text-slate-950">{title}</p>
        <span className="shrink-0 text-sm font-medium text-slate-500">{count}</span>
      </div>
      <div className="mt-4 space-y-3">
        {items.map(([name, meta]) => (
          <div key={name} className="rounded-2xl border border-slate-200 bg-white p-3">
            <p className="text-sm font-medium leading-6 text-slate-900">{name}</p>
            <p className="mt-2 text-xs font-medium uppercase tracking-[0.16em] text-slate-500">{meta}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

function DeadlineRow({ name, date }) {
  return (
    <div className="flex items-start justify-between gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-3">
      <span className="text-sm font-medium leading-6 text-slate-900">{name}</span>
      <span className="shrink-0 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-emerald-700">
        {date}
      </span>
    </div>
  )
}

function CommentBubble({ author, message, muted = false }) {
  return (
    <div className={`rounded-2xl border px-4 py-3 ${muted ? 'border-slate-200 bg-[#f8faf9]' : 'border-emerald-100 bg-emerald-50'}`}>
      <p className="text-sm font-semibold text-slate-900">{author}</p>
      <p className="mt-2 text-sm leading-6 text-slate-600">{message}</p>
    </div>
  )
}

function ProgressRow({ label, value }) {
  return (
    <div>
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium text-slate-700">{label}</span>
        <span className="text-slate-500">{value}</span>
      </div>
      <div className="mt-2 h-2 rounded-full bg-slate-200">
        <div className="h-2 rounded-full bg-emerald-600" style={{ width: value }} />
      </div>
    </div>
  )
}

function AvatarGroup() {
  return (
    <div className="flex -space-x-2">
      {['MJ', 'NT', 'AK', '+4'].map((avatar, index) => (
        <div
          key={avatar}
          className={`flex h-10 w-10 items-center justify-center rounded-full border-2 border-white text-xs font-semibold ${
            index === 3 ? 'bg-slate-900 text-white' : 'bg-emerald-100 text-emerald-700'
          }`}
        >
          {avatar}
        </div>
      ))}
    </div>
  )
}

function SimpleStat({ label, value }) {
  return (
    <div className="rounded-[20px] border border-slate-200 bg-white px-4 py-4">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-bold tracking-tight text-slate-950">{value}</p>
    </div>
  )
}

function MemberRow({ name, role }) {
  return (
    <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-[#fcfcfb] px-4 py-3">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-50 text-xs font-semibold text-emerald-700">
          {name
            .split(' ')
            .map((part) => part[0])
            .join('')}
        </div>
        <span className="text-sm font-medium text-slate-900">{name}</span>
      </div>
      <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{role}</span>
    </div>
  )
}

function NotificationRow({ title, time }) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-[#fcfcfb] px-4 py-3">
      <div className="flex items-center gap-3">
        <span className="h-2.5 w-2.5 rounded-full bg-emerald-600" />
        <span className="text-sm font-medium text-slate-900">{title}</span>
      </div>
      <span className="text-xs font-medium uppercase tracking-[0.16em] text-slate-500">{time}</span>
    </div>
  )
}

function MetricCard({ title, value }) {
  return (
    <div className="rounded-[22px] border border-slate-200 bg-white p-5">
      <p className="text-sm text-slate-500">{title}</p>
      <p className="mt-3 text-3xl font-bold tracking-tight text-slate-950">{value}</p>
    </div>
  )
}

function CalendarEvent({ day, month, title }) {
  return (
    <div className="flex items-center gap-4 rounded-2xl border border-slate-200 bg-white px-4 py-3">
      <div className="flex h-14 w-14 flex-col items-center justify-center rounded-2xl bg-emerald-50">
        <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-emerald-700">{month}</span>
        <span className="text-lg font-bold text-slate-950">{day}</span>
      </div>
      <div>
        <p className="text-sm font-medium text-slate-900">{title}</p>
        <p className="mt-1 text-sm text-slate-500">Calendar deadline view</p>
      </div>
    </div>
  )
}

function PlusIcon(props) {
  return (
    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" {...props}>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M12 5v14M5 12h14" />
    </svg>
  )
}

function CalendarIcon(props) {
  return (
    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" {...props}>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M7 3v3M17 3v3M4 9h16M5 5h14a1 1 0 0 1 1 1v13H4V6a1 1 0 0 1 1-1Z" />
    </svg>
  )
}

function ChatIcon(props) {
  return (
    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" {...props}>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M8 10h8M8 14h5M5 19V6a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H9l-4 3Z" />
    </svg>
  )
}

function BellIcon(props) {
  return (
    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" {...props}>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M15 17h5l-1.4-1.4a2 2 0 0 1-.6-1.44V11a6 6 0 1 0-12 0v3.16c0 .54-.21 1.05-.6 1.44L4 17h5m6 0v1a3 3 0 1 1-6 0v-1m6 0H9" />
    </svg>
  )
}

function ShieldIcon(props) {
  return (
    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" {...props}>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="m12 3 7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3Z" />
    </svg>
  )
}

function ChartIcon(props) {
  return (
    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" {...props}>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M5 19V9M12 19V5M19 19v-7" />
    </svg>
  )
}

function GitHubIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" {...props}>
      <path d="M12 .5C5.65.5.5 5.65.5 12c0 5.08 3.29 9.39 7.86 10.9.58.1.79-.25.79-.56 0-.28-.01-1.19-.02-2.15-3.2.7-3.88-1.36-3.88-1.36-.52-1.33-1.28-1.68-1.28-1.68-1.04-.71.08-.69.08-.69 1.16.08 1.76 1.18 1.76 1.18 1.02 1.76 2.68 1.25 3.33.96.1-.74.4-1.25.72-1.54-2.55-.29-5.24-1.28-5.24-5.68 0-1.25.45-2.28 1.18-3.08-.12-.29-.51-1.46.11-3.04 0 0 .97-.31 3.17 1.18a10.98 10.98 0 0 1 5.77 0c2.2-1.49 3.17-1.18 3.17-1.18.62 1.58.23 2.75.11 3.04.73.8 1.18 1.83 1.18 3.08 0 4.41-2.7 5.39-5.27 5.67.41.35.78 1.05.78 2.11 0 1.52-.01 2.75-.01 3.13 0 .31.21.67.8.56A11.5 11.5 0 0 0 23.5 12C23.5 5.65 18.35.5 12 .5Z" />
    </svg>
  )
}
