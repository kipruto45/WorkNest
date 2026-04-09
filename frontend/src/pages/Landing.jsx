import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import AppLogo from '../components/AppLogo'

const navItems = [
  { label: 'Features', href: '#features' },
  { label: 'Workflow', href: '#workflow' },
  { label: 'Collaboration', href: '#collaboration' },
  { label: 'Insights', href: '#insights' },
  { label: 'Contact', to: '/contact' },
]

const trustStats = [
  { value: '2,400+', label: 'teams launched into structured delivery' },
  { value: '1.8M', label: 'tasks planned, assigned, and completed' },
  { value: '99.9%', label: 'platform uptime for active workspaces' },
  { value: '< 10 min', label: 'to set up a new workspace with roles' },
]

const featureCards = [
  {
    title: 'Task capture that stays crisp under pressure',
    description: 'Create work with ownership, due dates, priorities, and context before anything slips into chat or private notes.',
    icon: TaskIcon,
  },
  {
    title: 'Assignments teams can actually trust',
    description: 'Every task carries a clear owner, delivery state, and next step so handoffs do not create ambiguity.',
    icon: PeopleIcon,
  },
  {
    title: 'Deadlines that stay visible',
    description: 'Calendar views, milestone context, and overdue alerts keep timing visible without turning the workspace into noise.',
    icon: DeadlineIcon,
  },
  {
    title: 'Comments where decisions happen',
    description: 'Mentions, replies, and task history live inside the work item, keeping collaboration tied to execution.',
    icon: CommentIcon,
  },
  {
    title: 'Permission controls for real teams',
    description: 'Set roles, manage invitations, and keep each workspace organized without a heavy admin layer.',
    icon: ShieldIcon,
  },
  {
    title: 'Operational visibility for managers',
    description: 'See workload, overdue items, completion trends, and blocked work in one focused operating view.',
    icon: InsightIcon,
  },
]

const workflowPoints = [
  'Create tasks with enough structure to move immediately.',
  'Assign work, share context, and confirm due dates in one step.',
  'Track execution across boards, milestones, and personal views.',
]

const collaborationPoints = [
  'Shared updates and mentions live on the task itself.',
  'Managers can rebalance ownership before deadlines slip.',
  'Invites, permissions, and team progress stay in one system.',
]

const analyticsPoints = [
  'Overdue work is visible without digging through reports.',
  'Completion pace and team capacity stay readable week to week.',
  'Leads can spot concentration risk before it becomes delay.',
]

const footerColumns = [
  {
    title: 'Product',
    links: [
      { label: 'Features', href: '#features' },
      { label: 'Workflow', href: '#workflow' },
      { label: 'Collaboration', href: '#collaboration' },
      { label: 'Insights', href: '#insights' },
    ],
  },
  {
    title: 'Company',
    links: [
      { label: 'About', to: '/about' },
      { label: 'Contact', to: '/contact' },
      { label: 'Support', to: '/support' },
      { label: 'Status', to: '/status' },
    ],
  },
  {
    title: 'Resources',
    links: [
      { label: 'Help Center', to: '/help-center' },
      { label: 'API Docs', to: '/api-docs' },
      { label: 'Security', to: '/security' },
      { label: 'Support Desk', to: '/support' },
    ],
  },
]

const containerClass = 'mx-auto w-full max-w-[1240px] px-6 lg:px-8'
const primaryButtonClass =
  'inline-flex min-h-[46px] items-center justify-center gap-2 rounded-xl bg-[#315efb] px-5 text-sm font-semibold text-white shadow-[0_14px_28px_rgba(49,94,251,0.2)] transition-all duration-200 hover:-translate-y-0.5 hover:bg-[#244ee6] hover:shadow-[0_18px_34px_rgba(49,94,251,0.24)]'
const secondaryButtonClass =
  'inline-flex min-h-[46px] items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-5 text-sm font-semibold text-slate-900 transition-all duration-200 hover:-translate-y-0.5 hover:border-slate-400 hover:bg-slate-50'
const panelClass =
  'rounded-[28px] border border-slate-200/80 bg-white shadow-[0_24px_60px_rgba(15,23,42,0.07)]'

export default function Landing() {
  const [isScrolled, setIsScrolled] = useState(false)

  useEffect(() => {
    const onScroll = () => setIsScrolled(window.scrollY > 12)

    onScroll()
    window.addEventListener('scroll', onScroll)

    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <div className="relative isolate min-h-screen overflow-x-clip bg-[#f5f6f8] text-slate-950">
      <div className="absolute inset-x-0 top-0 -z-10 h-[720px] bg-[radial-gradient(circle_at_top,rgba(49,94,251,0.08),transparent_32%),linear-gradient(180deg,#f8f8fa_0%,#f5f6f8_100%)]" />

      <header
        className={`sticky top-0 z-50 border-b transition-all duration-300 ${
          isScrolled ? 'border-slate-200/80 bg-[rgba(245,246,248,0.86)] backdrop-blur-xl' : 'border-transparent bg-transparent'
        }`}
      >
        <div className={containerClass}>
          <div className="flex h-20 items-center justify-between gap-6">
            <AppLogo
              to="/"
              subtitle="Structured task operations"
              imageClassName="h-10 w-10"
              titleClassName="text-[13px] font-semibold uppercase tracking-[0.22em] text-slate-950"
              subtitleClassName="text-sm text-slate-500"
            />

            <nav className="hidden items-center gap-8 lg:flex">
              {navItems.map((item) =>
                item.to ? (
                  <Link
                    key={item.label}
                    to={item.to}
                    className="text-sm font-medium text-slate-600 transition-colors duration-200 hover:text-slate-950"
                  >
                    {item.label}
                  </Link>
                ) : (
                  <a
                    key={item.href}
                    href={item.href}
                    className="text-sm font-medium text-slate-600 transition-colors duration-200 hover:text-slate-950"
                  >
                    {item.label}
                  </a>
                )
              )}
            </nav>

            <div className="flex items-center gap-3">
              <Link to="/login" className="hidden text-sm font-semibold text-slate-700 transition-colors hover:text-slate-950 sm:inline-flex">
                Sign in
              </Link>
              <Link to="/register" className={primaryButtonClass}>
                Start free
              </Link>
            </div>
          </div>
        </div>
      </header>

      <main>
        <section className="relative overflow-hidden pb-24 pt-10 md:pb-28 md:pt-16">
          <div className={containerClass}>
            <div className="grid items-center gap-16 lg:grid-cols-[minmax(0,0.88fr)_minmax(0,1.12fr)]">
              <div className="fade-in">
                <div className="inline-flex items-center rounded-full border border-[#cad6ff] bg-[#eef2ff] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-[#244ee6]">
                  Built for product, operations, and delivery teams
                </div>
                <h1 className="mt-7 max-w-[11ch] text-balance font-display text-[3.35rem] font-bold leading-[0.95] tracking-[-0.05em] text-slate-950 md:text-[4.6rem]">
                  Work that moves with clarity.
                </h1>
                <p className="mt-6 max-w-[34rem] text-lg leading-8 text-slate-600">
                  WorkNest gives modern teams one calm, structured place to plan tasks, assign ownership, track deadlines,
                  and keep delivery visible from kickoff to completion.
                </p>

                <div className="mt-9 flex flex-wrap gap-3">
                  <Link to="/register" className={primaryButtonClass}>
                    Start your workspace
                    <ArrowRightIcon className="h-4 w-4" />
                  </Link>
                  <a href="#workflow" className={secondaryButtonClass}>
                    View product tour
                    <PlayIcon className="h-4 w-4" />
                  </a>
                </div>

                <div className="mt-5 flex flex-wrap items-center gap-x-5 gap-y-3 text-sm text-slate-500">
                  <div className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-[#315efb]" />
                    No credit card required
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-[#315efb]" />
                    Roles, permissions, and notifications included
                  </div>
                </div>

                <div className="mt-10 rounded-2xl border border-slate-200/80 bg-white/90 px-5 py-4 shadow-[0_16px_42px_rgba(15,23,42,0.05)]">
                  <div className="flex items-start gap-4">
                    <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-[#eef2ff] text-[#244ee6]">
                      <SparkIcon className="h-5 w-5" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-slate-950">Trusted by teams that need a steadier operating rhythm</p>
                      <p className="mt-1 text-sm leading-6 text-slate-600">
                        Setup stays lightweight, while the workspace feels robust enough for real deadlines, ownership, and cross-team coordination.
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="fade-in-delayed">
                <HeroWorkspacePreview />
              </div>
            </div>
          </div>
        </section>

        <section className="border-y border-slate-200/80 bg-white">
          <div className={containerClass}>
            <div className="flex flex-col gap-8 py-7 lg:flex-row lg:items-center lg:justify-between">
              <div className="max-w-[28rem]">
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Operational proof</p>
                <p className="mt-2 text-lg font-semibold tracking-tight text-slate-950">
                  Designed for teams that need cleaner execution, not louder software.
                </p>
              </div>

              <div className="grid flex-1 gap-5 sm:grid-cols-2 xl:grid-cols-4">
                {trustStats.map((item) => (
                  <div key={item.label} className="rounded-2xl border border-slate-200/70 bg-slate-50/80 px-4 py-4">
                    <div className="text-2xl font-semibold tracking-tight text-slate-950">{item.value}</div>
                    <div className="mt-1 text-sm leading-6 text-slate-600">{item.label}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section id="features" className="scroll-mt-28 py-24 md:py-28">
          <div className={containerClass}>
            <SectionIntro
              eyebrow="Features"
              title="A serious workspace for teams that want execution to stay readable."
              description="Every part of WorkNest is designed to reduce ambiguity: clearer task intake, visible deadlines, stronger accountability, and collaboration that stays attached to the work."
            />

            <div className="mt-14 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
              {featureCards.map((feature) => {
                const Icon = feature.icon
                return (
                  <article
                    key={feature.title}
                    className="group rounded-[26px] border border-slate-200/80 bg-white p-6 shadow-[0_14px_42px_rgba(15,23,42,0.05)] transition-all duration-300 hover:-translate-y-1 hover:border-slate-300 hover:shadow-[0_20px_50px_rgba(15,23,42,0.08)]"
                  >
                    <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[#eef2ff] text-[#244ee6] transition-transform duration-300 group-hover:-translate-y-0.5">
                      <Icon className="h-5 w-5" />
                    </div>
                    <h3 className="mt-5 max-w-[18ch] text-xl font-semibold tracking-tight text-slate-950">{feature.title}</h3>
                    <p className="mt-3 text-sm leading-7 text-slate-600">{feature.description}</p>
                  </article>
                )
              })}
            </div>
          </div>
        </section>

        <section id="workflow" className="scroll-mt-28 border-y border-slate-200/80 bg-white py-24 md:py-28">
          <div className={containerClass}>
            <div className="grid items-start gap-14 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
              <div className="fade-in">
                <SectionIntro
                  eyebrow="Product Showcase"
                  title="From intake to delivery, the workflow stays intentional."
                  description="Capture new work, assign the right owner, keep deadlines visible, and maintain context in the task itself. The interface stays calm even when the work queue grows."
                  align="left"
                />

                <div className="mt-9 space-y-4">
                  {workflowPoints.map((point, index) => (
                    <div key={point} className="flex gap-4 rounded-2xl border border-slate-200/80 bg-slate-50/80 px-4 py-4">
                      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-slate-900 text-sm font-semibold text-white">
                        {index + 1}
                      </div>
                      <p className="pt-0.5 text-sm leading-7 text-slate-600">{point}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="fade-in-delayed">
                <WorkflowShowcase />
              </div>
            </div>
          </div>
        </section>

        <section id="collaboration" className="scroll-mt-28 py-24 md:py-28">
          <div className={containerClass}>
            <div className="grid items-center gap-14 lg:grid-cols-[minmax(0,1.08fr)_minmax(0,0.92fr)]">
              <div className="fade-in">
                <CollaborationShowcase />
              </div>

              <div className="fade-in-delayed">
                <SectionIntro
                  eyebrow="Team Collaboration"
                  title="Shared context keeps work moving without extra meetings."
                  description="Managers, contributors, and stakeholders can see the same decisions, ownership, and progress without chasing updates across tools."
                  align="left"
                />

                <div className="mt-9 space-y-4">
                  {collaborationPoints.map((point) => (
                    <div key={point} className="flex items-start gap-3">
                      <span className="mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[#eef2ff] text-[#244ee6]">
                        <CheckIcon className="h-3.5 w-3.5" />
                      </span>
                      <p className="text-sm leading-7 text-slate-600">{point}</p>
                    </div>
                  ))}
                </div>

                <div className="mt-8 grid gap-4 sm:grid-cols-3">
                  <MiniStat label="Shared updates" value="100%" />
                  <MiniStat label="Pending invites" value="03" />
                  <MiniStat label="Owners confirmed" value="94%" />
                </div>
              </div>
            </div>
          </div>
        </section>

        <section id="insights" className="scroll-mt-28 border-y border-slate-200/80 bg-white py-24 md:py-28">
          <div className={containerClass}>
            <div className="grid items-start gap-14 lg:grid-cols-[minmax(0,0.92fr)_minmax(0,1.08fr)]">
              <div className="fade-in">
                <SectionIntro
                  eyebrow="Dashboard & Analytics"
                  title="The operating view leaders need, without analytics overload."
                  description="WorkNest surfaces overdue tasks, completion pace, capacity pressure, and delivery trends in a format that stays clear at a glance."
                  align="left"
                />

                <div className="mt-9 space-y-4">
                  {analyticsPoints.map((point) => (
                    <div key={point} className="rounded-2xl border border-slate-200/80 bg-slate-50/80 px-4 py-4 text-sm leading-7 text-slate-600">
                      {point}
                    </div>
                  ))}
                </div>
              </div>

              <div className="fade-in-delayed">
                <AnalyticsShowcase />
              </div>
            </div>
          </div>
        </section>

        <section className="py-24 md:py-28">
          <div className={containerClass}>
            <div className="overflow-hidden rounded-[34px] border border-slate-200 bg-slate-950 px-6 py-12 text-white shadow-[0_26px_64px_rgba(2,6,23,0.18)] md:px-10">
              <div className="grid gap-8 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)] lg:items-center">
                <div>
                  <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#9bb2ff]">Final CTA</p>
                  <h2 className="mt-4 max-w-[12ch] text-balance font-display text-4xl font-bold tracking-[-0.04em] md:text-[3.4rem]">
                    Give your team a calmer way to run work.
                  </h2>
                  <p className="mt-4 max-w-[36rem] text-base leading-8 text-slate-300">
                    Launch a structured workspace for tasks, deadlines, and collaboration without the overhead of a bloated enterprise rollout.
                  </p>
                </div>

                <div className="flex flex-wrap gap-3 lg:justify-end">
                  <Link to="/register" className="inline-flex min-h-[48px] items-center justify-center gap-2 rounded-xl bg-white px-5 text-sm font-semibold text-slate-950 transition-all duration-200 hover:-translate-y-0.5 hover:bg-slate-100">
                    Create your workspace
                    <ArrowRightIcon className="h-4 w-4" />
                  </Link>
                  <Link to="/contact" className="inline-flex min-h-[48px] items-center justify-center rounded-xl border border-white/20 px-5 text-sm font-semibold text-white transition-colors duration-200 hover:bg-white/6">
                    Talk to us
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-slate-200/80 bg-white">
        <div className={containerClass}>
          <div className="grid gap-12 py-14 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
            <div>
              <AppLogo
                subtitle="Task operations for modern teams"
                imageClassName="h-10 w-10"
                titleClassName="text-[13px] font-semibold uppercase tracking-[0.22em] text-slate-950"
                subtitleClassName="text-sm text-slate-500"
              />
              <p className="mt-5 max-w-[34rem] text-sm leading-7 text-slate-600">
                WorkNest helps teams plan work, confirm ownership, keep deadlines visible, and collaborate in context with a more polished operating rhythm.
              </p>

              <div className="mt-6 flex flex-wrap gap-x-6 gap-y-3 text-sm font-medium text-slate-500">
                <a href="mailto:support@worknest.example" className="transition-colors hover:text-slate-950">
                  support@worknest.example
                </a>
                <Link to="/status" className="transition-colors hover:text-slate-950">
                  System status
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
                    {column.links.map((item) =>
                      item.to ? (
                        <Link key={item.label} to={item.to} className="block text-sm text-slate-600 transition-colors hover:text-slate-950">
                          {item.label}
                        </Link>
                      ) : (
                        <a key={item.label} href={item.href} className="block text-sm text-slate-600 transition-colors hover:text-slate-950">
                          {item.label}
                        </a>
                      )
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-3 border-t border-slate-200/80 py-6 text-sm text-slate-500 sm:flex-row sm:items-center sm:justify-between">
            <p>© 2026 WorkNest. All rights reserved.</p>
            <div className="flex items-center gap-5">
              <Link to="/about" className="transition-colors hover:text-slate-950">
                About
              </Link>
              <Link to="/support" className="transition-colors hover:text-slate-950">
                Support
              </Link>
              <a href="https://github.com/kipruto45" target="_blank" rel="noreferrer" className="transition-colors hover:text-slate-950">
                GitHub
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}

function SectionIntro({ eyebrow, title, description, align = 'center' }) {
  const wrapperClass = align === 'left' ? 'max-w-[34rem]' : 'mx-auto max-w-[46rem] text-center'
  const titleClass = align === 'left' ? '' : 'mx-auto'

  return (
    <div className={wrapperClass}>
      <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#315efb]">{eyebrow}</p>
      <h2 className={`mt-4 text-balance font-display text-4xl font-bold tracking-[-0.04em] text-slate-950 md:text-[3rem] ${titleClass}`}>
        {title}
      </h2>
      <p className="mt-4 text-base leading-8 text-slate-600">{description}</p>
    </div>
  )
}

function MiniStat({ label, value }) {
  return (
    <div className="rounded-2xl border border-slate-200/80 bg-white px-4 py-4 shadow-[0_12px_30px_rgba(15,23,42,0.04)]">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">{value}</p>
    </div>
  )
}

function HeroWorkspacePreview() {
  return (
    <div className={`${panelClass} mx-auto w-full max-w-[860px] overflow-hidden`}>
      <WindowHeader title="WorkNest workspace" path="app.worknest.com/releases" />

      <div className="grid gap-5 bg-[linear-gradient(180deg,#fafbff_0%,#f7f8fc_100%)] p-5 lg:grid-cols-[188px_minmax(0,1fr)]">
        <aside className="rounded-[24px] border border-slate-200/80 bg-white p-4">
          <div className="rounded-2xl bg-slate-950 px-4 py-4 text-white">
            <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">June release</div>
            <div className="mt-2 text-3xl font-semibold tracking-tight">42</div>
            <div className="mt-1 text-sm text-slate-300">active items across the launch plan</div>
          </div>

          <div className="mt-4 space-y-2">
            <SidebarPill label="Overview" active />
            <SidebarPill label="Team board" />
            <SidebarPill label="Milestones" />
            <SidebarPill label="Activity" />
          </div>
        </aside>

        <div className="space-y-4">
          <div className="grid gap-4 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
            <div className="rounded-[24px] border border-slate-200/80 bg-white p-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="text-xs font-semibold uppercase tracking-[0.18em] text-[#315efb]">Weekly board</div>
                  <h3 className="mt-2 text-xl font-semibold tracking-tight text-slate-950">Launch readiness</h3>
                </div>
                <div className="rounded-full border border-[#cad6ff] bg-[#eef2ff] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-[#244ee6]">
                  On track
                </div>
              </div>

              <div className="mt-4 grid gap-3 sm:grid-cols-3">
                <PreviewColumn
                  title="Ready"
                  count="14"
                  items={[
                    { title: 'Launch QA checklist', meta: 'Amina · Due today' },
                    { title: 'Comms review', meta: 'Sara · Approved' },
                  ]}
                />
                <PreviewColumn
                  title="In progress"
                  count="09"
                  items={[
                    { title: 'Migration dry run', meta: 'Daniel · 3 blockers cleared' },
                    { title: 'Support macros', meta: 'Ivy · In review' },
                  ]}
                />
                <PreviewColumn
                  title="Next"
                  count="19"
                  items={[
                    { title: 'Ops sign-off', meta: 'Pending owner review' },
                    { title: 'Final release notes', meta: 'Drafting window' },
                  ]}
                />
              </div>
            </div>

            <div className="rounded-[24px] border border-slate-200/80 bg-white p-4">
              <div className="text-sm font-semibold text-slate-950">Today&apos;s execution view</div>
              <div className="mt-4 space-y-3">
                <ExecutionItem title="High priority" value="07" tone="red" />
                <ExecutionItem title="Due this week" value="13" tone="blue" />
                <ExecutionItem title="Awaiting review" value="05" tone="slate" />
              </div>
              <div className="mt-4 rounded-2xl bg-slate-50 px-4 py-4">
                <div className="flex items-center justify-between text-sm text-slate-500">
                  <span>Delivery confidence</span>
                  <span className="font-semibold text-slate-950">82%</span>
                </div>
                <div className="mt-3 h-2 rounded-full bg-slate-200">
                  <div className="h-full w-[82%] rounded-full bg-[#315efb]" />
                </div>
              </div>
            </div>
          </div>

          <div className="grid gap-4 xl:grid-cols-[minmax(0,0.94fr)_minmax(0,1.06fr)]">
            <div className="rounded-[24px] border border-slate-200/80 bg-white p-4">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <div className="text-sm font-semibold text-slate-950">Upcoming deadlines</div>
                  <div className="mt-1 text-sm text-slate-500">Nothing gets buried under status noise.</div>
                </div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[#315efb]">Calendar sync</div>
              </div>
              <div className="mt-4 space-y-3">
                <DeadlineRow title="Customer migration handoff" due="Today" owner="Amina" />
                <DeadlineRow title="Support enablement review" due="Thu" owner="Ivy" />
                <DeadlineRow title="Release memo" due="Fri" owner="Daniel" />
              </div>
            </div>

            <div className="rounded-[24px] border border-slate-200/80 bg-white p-4">
              <div className="flex items-center justify-between">
                <div className="text-sm font-semibold text-slate-950">Team activity</div>
                <AvatarStack />
              </div>
              <div className="mt-4 space-y-3">
                <ActivityRow person="Maya" message="Moved migration dry run into review and tagged support." />
                <ActivityRow person="Amina" message="Updated launch checklist with final approval steps." />
                <ActivityRow person="Ivy" message="Confirmed macro rollout plan for day-one tickets." />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function WorkflowShowcase() {
  return (
    <div className="space-y-4">
      <div className={`${panelClass} overflow-hidden`}>
        <WindowHeader title="New task intake" path="workspace/intake" />
        <div className="grid gap-4 bg-[linear-gradient(180deg,#ffffff_0%,#f8f9fd_100%)] p-5 lg:grid-cols-[minmax(0,0.98fr)_minmax(0,1.02fr)]">
          <div className="rounded-[24px] border border-slate-200/80 bg-white p-5">
            <div className="text-xs font-semibold uppercase tracking-[0.18em] text-[#315efb]">Create task</div>
            <h3 className="mt-2 text-xl font-semibold tracking-tight text-slate-950">Prepare onboarding launch notes</h3>
            <p className="mt-2 text-sm leading-7 text-slate-600">
              A clean task form makes the owner, timing, and expected output obvious from the start.
            </p>

            <div className="mt-5 space-y-3">
              <Field label="Owner" value="Maya Chen" />
              <Field label="Due date" value="June 18" />
              <Field label="Priority" value="High" />
              <Field label="Milestone" value="June release" />
            </div>
          </div>

          <div className="rounded-[24px] border border-slate-200/80 bg-white p-5">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-semibold text-slate-950">Assignment confirmation</div>
                <div className="mt-1 text-sm text-slate-500">The handoff is explicit before work starts.</div>
              </div>
              <div className="rounded-full bg-[#eef2ff] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-[#244ee6]">
                Ready
              </div>
            </div>

            <div className="mt-5 space-y-4">
              <AssignmentRow label="Design review" owner="Taylor" state="Confirmed" />
              <AssignmentRow label="QA checklist" owner="Amina" state="Confirmed" />
              <AssignmentRow label="Release note draft" owner="Maya" state="In progress" />
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.12fr)_minmax(0,0.88fr)]">
        <div className={`${panelClass} overflow-hidden`}>
          <div className="border-b border-slate-200/80 bg-slate-50/80 px-5 py-4">
            <div className="text-sm font-semibold text-slate-950">Task board</div>
          </div>
          <div className="grid gap-3 p-5 md:grid-cols-3">
            <WorkflowColumn
              title="Plan"
              items={[
                'Confirm rollout owner',
                'Review support macros',
              ]}
            />
            <WorkflowColumn
              title="Execute"
              items={[
                'Finalize migration runbook',
                'Ship customer comms',
              ]}
            />
            <WorkflowColumn
              title="Review"
              items={[
                'Collect QA sign-off',
                'Approve final notes',
              ]}
            />
          </div>
        </div>

        <div className={`${panelClass} overflow-hidden`}>
          <div className="border-b border-slate-200/80 bg-slate-50/80 px-5 py-4">
            <div className="text-sm font-semibold text-slate-950">Deadline focus</div>
          </div>
          <div className="space-y-3 p-5">
            <TimelineRow title="Dry run rehearsal" date="Today" completion={92} />
            <TimelineRow title="Support handoff" date="Thu" completion={68} />
            <TimelineRow title="Launch readiness review" date="Fri" completion={48} />
          </div>
        </div>
      </div>
    </div>
  )
}

function CollaborationShowcase() {
  return (
    <div className="space-y-4">
      <div className={`${panelClass} overflow-hidden`}>
        <WindowHeader title="Team workspace" path="workspace/collaboration" />
        <div className="grid gap-4 bg-[linear-gradient(180deg,#fafbff_0%,#f6f7fb_100%)] p-5 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
          <div className="rounded-[24px] border border-slate-200/80 bg-white p-5">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.18em] text-[#315efb]">Delivery team</div>
                <h3 className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">Launch squad</h3>
              </div>
              <AvatarStack />
            </div>

            <div className="mt-5 grid gap-3 sm:grid-cols-3">
              <TeamMiniCard label="Members" value="14" />
              <TeamMiniCard label="Open tasks" value="38" />
              <TeamMiniCard label="In review" value="06" />
            </div>

            <div className="mt-5 rounded-[22px] bg-slate-50 px-4 py-4">
              <div className="text-sm font-semibold text-slate-950">Role coverage</div>
              <div className="mt-3 space-y-3">
                <RoleRow role="Project lead" person="Amina" />
                <RoleRow role="Support enablement" person="Ivy" />
                <RoleRow role="Product comms" person="Maya" />
              </div>
            </div>
          </div>

          <div className="rounded-[24px] border border-slate-200/80 bg-white p-5">
            <div className="flex items-center justify-between">
              <div className="text-sm font-semibold text-slate-950">Discussion in context</div>
              <div className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-600">
                3 mentions
              </div>
            </div>

            <div className="mt-4 space-y-4">
              <CommentBubble
                author="Maya"
                role="Product"
                message="Copy is final. I tagged support so they can confirm the escalation macro before launch."
              />
              <CommentBubble
                author="Ivy"
                role="Support"
                message="Confirmed. The handoff article is attached and the macro is ready for the Friday deployment."
                subtle
              />
              <CommentBubble
                author="Amina"
                role="Ops"
                message="Perfect. I moved the release memo into review and attached the final checklist to the milestone."
              />
            </div>
          </div>
        </div>
      </div>

      <div className={`${panelClass} overflow-hidden`}>
        <div className="border-b border-slate-200/80 bg-slate-50/80 px-5 py-4">
          <div className="text-sm font-semibold text-slate-950">Shared progress</div>
        </div>
        <div className="grid gap-4 p-5 md:grid-cols-[minmax(0,1.08fr)_minmax(0,0.92fr)]">
          <div className="rounded-[22px] border border-slate-200/80 bg-white p-4">
            <div className="text-sm font-semibold text-slate-950">Assignment health</div>
            <div className="mt-4 space-y-4">
              <CapacityRow name="Amina" load="Balanced" percentage={74} />
              <CapacityRow name="Maya" load="Focused" percentage={61} />
              <CapacityRow name="Ivy" load="High attention" percentage={88} />
            </div>
          </div>

          <div className="rounded-[22px] border border-slate-200/80 bg-white p-4">
            <div className="text-sm font-semibold text-slate-950">Progress by lane</div>
            <div className="mt-4 space-y-4">
              <LaneRow lane="Planning" value="100%" />
              <LaneRow lane="Execution" value="78%" />
              <LaneRow lane="Review" value="51%" />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function AnalyticsShowcase() {
  return (
    <div className={`${panelClass} overflow-hidden`}>
      <WindowHeader title="Insights dashboard" path="workspace/insights" />
      <div className="space-y-4 bg-[linear-gradient(180deg,#ffffff_0%,#f8f9fd_100%)] p-5">
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <InsightCard label="Overdue tasks" value="12" tone="red" />
          <InsightCard label="Completed this week" value="184" tone="blue" />
          <InsightCard label="Team capacity" value="76%" tone="slate" />
          <InsightCard label="Blocked items" value="03" tone="amber" />
        </div>

        <div className="grid gap-4 xl:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]">
          <div className="rounded-[24px] border border-slate-200/80 bg-white p-5">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-semibold text-slate-950">Completion pace</div>
                <div className="mt-1 text-sm text-slate-500">A clean weekly signal instead of report overload.</div>
              </div>
              <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[#315efb]">Last 6 weeks</div>
            </div>

            <div className="mt-6 flex h-56 items-end justify-between gap-3">
              {[46, 58, 71, 64, 79, 88].map((height, index) => (
                <div key={height} className="flex flex-1 flex-col items-center gap-3">
                  <div className="flex w-full flex-1 items-end">
                    <div
                      className={`w-full rounded-t-[18px] ${
                        index === 5 ? 'bg-[#315efb]' : 'bg-slate-200'
                      }`}
                      style={{ height: `${height}%` }}
                    />
                  </div>
                  <span className="text-xs font-medium text-slate-500">W{index + 1}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-4">
            <div className="rounded-[24px] border border-slate-200/80 bg-white p-5">
              <div className="text-sm font-semibold text-slate-950">Workload visibility</div>
              <div className="mt-4 space-y-4">
                <WorkloadRow name="Product" current="18 active" balance="Healthy" />
                <WorkloadRow name="Operations" current="23 active" balance="Watchlist" />
                <WorkloadRow name="Support" current="11 active" balance="Healthy" />
              </div>
            </div>

            <div className="rounded-[24px] border border-slate-200/80 bg-slate-950 p-5 text-white">
              <div className="text-sm font-semibold text-white">Delivery summary</div>
              <div className="mt-5 grid gap-4 sm:grid-cols-2">
                <DarkMetric label="Milestones on track" value="08" />
                <DarkMetric label="Escalations open" value="02" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function WindowHeader({ title, path }) {
  return (
    <div className="flex items-center justify-between border-b border-slate-200/80 bg-slate-50/80 px-5 py-3.5">
      <div className="flex items-center gap-2.5">
        <span className="h-2.5 w-2.5 rounded-full bg-[#f97066]" />
        <span className="h-2.5 w-2.5 rounded-full bg-[#f9b548]" />
        <span className="h-2.5 w-2.5 rounded-full bg-[#32d583]" />
      </div>
      <div className="min-w-0 flex-1 px-4 text-center">
        <div className="truncate text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{title}</div>
      </div>
      <div className="hidden rounded-full border border-slate-200 bg-white px-3 py-1 text-[11px] font-medium text-slate-500 sm:block">
        {path}
      </div>
    </div>
  )
}

function SidebarPill({ label, active = false }) {
  return (
    <div
      className={`rounded-2xl px-4 py-3 text-sm font-medium transition-colors ${
        active ? 'bg-[#eef2ff] text-[#244ee6]' : 'bg-slate-50 text-slate-600'
      }`}
    >
      {label}
    </div>
  )
}

function PreviewColumn({ title, count, items }) {
  return (
    <div className="rounded-[20px] border border-slate-200/80 bg-slate-50/70 p-3">
      <div className="flex items-center justify-between">
        <div className="text-sm font-semibold text-slate-950">{title}</div>
        <div className="rounded-full bg-white px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">
          {count}
        </div>
      </div>
      <div className="mt-3 space-y-2.5">
        {items.map((item) => (
          <div key={item.title} className="rounded-2xl border border-white bg-white px-3 py-3 shadow-[0_6px_18px_rgba(15,23,42,0.04)]">
            <div className="text-sm font-medium text-slate-950">{item.title}</div>
            <div className="mt-1 text-xs leading-5 text-slate-500">{item.meta}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

function ExecutionItem({ title, value, tone }) {
  const toneClass = {
    red: 'bg-[#fef3f2] text-[#d92d20]',
    blue: 'bg-[#eef2ff] text-[#244ee6]',
    slate: 'bg-slate-100 text-slate-700',
  }[tone]

  return (
    <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
      <div className="text-sm font-medium text-slate-600">{title}</div>
      <div className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] ${toneClass}`}>{value}</div>
    </div>
  )
}

function DeadlineRow({ title, due, owner }) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-2xl border border-slate-200/70 bg-white px-4 py-3">
      <div className="min-w-0">
        <div className="truncate text-sm font-medium text-slate-950">{title}</div>
        <div className="mt-1 text-xs text-slate-500">{owner}</div>
      </div>
      <div className="rounded-full bg-slate-100 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-600">
        {due}
      </div>
    </div>
  )
}

function ActivityRow({ person, message }) {
  return (
    <div className="rounded-2xl border border-slate-200/70 bg-slate-50/80 px-4 py-3">
      <div className="text-sm font-semibold text-slate-950">{person}</div>
      <div className="mt-1 text-sm leading-6 text-slate-600">{message}</div>
    </div>
  )
}

function Field({ label, value }) {
  return (
    <div className="rounded-2xl border border-slate-200/80 bg-slate-50 px-4 py-3">
      <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">{label}</div>
      <div className="mt-1 text-sm font-medium text-slate-950">{value}</div>
    </div>
  )
}

function AssignmentRow({ label, owner, state }) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-2xl bg-slate-50 px-4 py-3">
      <div>
        <div className="text-sm font-medium text-slate-950">{label}</div>
        <div className="mt-1 text-xs text-slate-500">{owner}</div>
      </div>
      <div className="rounded-full border border-slate-200 bg-white px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-600">
        {state}
      </div>
    </div>
  )
}

function WorkflowColumn({ title, items }) {
  return (
    <div className="rounded-[22px] border border-slate-200/80 bg-slate-50/70 p-4">
      <div className="text-sm font-semibold text-slate-950">{title}</div>
      <div className="mt-3 space-y-2.5">
        {items.map((item) => (
          <div key={item} className="rounded-2xl border border-white bg-white px-3 py-3 text-sm font-medium text-slate-950 shadow-[0_6px_18px_rgba(15,23,42,0.04)]">
            {item}
          </div>
        ))}
      </div>
    </div>
  )
}

function TimelineRow({ title, date, completion }) {
  return (
    <div className="rounded-[22px] border border-slate-200/80 bg-white px-4 py-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <div className="text-sm font-medium text-slate-950">{title}</div>
          <div className="mt-1 text-xs text-slate-500">{date}</div>
        </div>
        <div className="text-sm font-semibold text-slate-950">{completion}%</div>
      </div>
      <div className="mt-3 h-2 rounded-full bg-slate-200">
        <div className="h-full rounded-full bg-[#315efb]" style={{ width: `${completion}%` }} />
      </div>
    </div>
  )
}

function TeamMiniCard({ label, value }) {
  return (
    <div className="rounded-[20px] border border-slate-200/80 bg-slate-50 px-4 py-4">
      <div className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{label}</div>
      <div className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">{value}</div>
    </div>
  )
}

function RoleRow({ role, person }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-2xl bg-white px-4 py-3">
      <div className="text-sm font-medium text-slate-950">{role}</div>
      <div className="text-sm text-slate-500">{person}</div>
    </div>
  )
}

function CommentBubble({ author, role, message, subtle = false }) {
  return (
    <div className={`rounded-[22px] px-4 py-4 ${subtle ? 'bg-slate-50' : 'bg-[#f8f9ff]'}`}>
      <div className="flex items-center gap-2">
        <span className="text-sm font-semibold text-slate-950">{author}</span>
        <span className="text-xs font-medium uppercase tracking-[0.16em] text-slate-500">{role}</span>
      </div>
      <div className="mt-2 text-sm leading-7 text-slate-600">{message}</div>
    </div>
  )
}

function CapacityRow({ name, load, percentage }) {
  return (
    <div>
      <div className="flex items-center justify-between gap-4 text-sm">
        <span className="font-medium text-slate-950">{name}</span>
        <span className="text-slate-500">{load}</span>
      </div>
      <div className="mt-2 h-2 rounded-full bg-slate-200">
        <div className="h-full rounded-full bg-[#315efb]" style={{ width: `${percentage}%` }} />
      </div>
    </div>
  )
}

function LaneRow({ lane, value }) {
  return (
    <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3 text-sm">
      <span className="font-medium text-slate-950">{lane}</span>
      <span className="font-semibold text-slate-600">{value}</span>
    </div>
  )
}

function InsightCard({ label, value, tone }) {
  const accent = {
    red: 'bg-[#fef3f2] text-[#d92d20]',
    blue: 'bg-[#eef2ff] text-[#244ee6]',
    slate: 'bg-slate-100 text-slate-700',
    amber: 'bg-[#fffaeb] text-[#b54708]',
  }[tone]

  return (
    <div className="rounded-[22px] border border-slate-200/80 bg-white px-4 py-4">
      <div className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{label}</div>
      <div className="mt-3 flex items-center justify-between gap-4">
        <div className="text-3xl font-semibold tracking-tight text-slate-950">{value}</div>
        <div className={`rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] ${accent}`}>Live</div>
      </div>
    </div>
  )
}

function WorkloadRow({ name, current, balance }) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-2xl bg-slate-50 px-4 py-3">
      <div>
        <div className="text-sm font-medium text-slate-950">{name}</div>
        <div className="mt-1 text-xs text-slate-500">{current}</div>
      </div>
      <div className="rounded-full border border-slate-200 bg-white px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-600">
        {balance}
      </div>
    </div>
  )
}

function DarkMetric({ label, value }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-4">
      <div className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">{label}</div>
      <div className="mt-2 text-2xl font-semibold tracking-tight text-white">{value}</div>
    </div>
  )
}

function AvatarStack() {
  return (
    <div className="flex -space-x-2">
      {['AM', 'MC', 'IV'].map((person, index) => (
        <div
          key={person}
          className={`flex h-9 w-9 items-center justify-center rounded-full border-2 border-white text-[11px] font-semibold text-white ${
            index === 0 ? 'bg-slate-900' : index === 1 ? 'bg-[#315efb]' : 'bg-[#0f766e]'
          }`}
        >
          {person}
        </div>
      ))}
    </div>
  )
}

function ArrowRightIcon(props) {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" {...props}>
      <path d="M4 10h11" strokeLinecap="round" />
      <path d="m10.5 4.5 5 5-5 5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function PlayIcon(props) {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" {...props}>
      <path d="M6.5 4.8c0-.7.8-1.13 1.4-.76l8.2 4.95a.9.9 0 0 1 0 1.54L7.9 15.48c-.62.37-1.4-.07-1.4-.78V4.8Z" />
    </svg>
  )
}

function SparkIcon(props) {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" {...props}>
      <path d="m10 2 1.8 4.7L16.5 8l-4.7 1.3L10 14l-1.8-4.7L3.5 8l4.7-1.3L10 2Z" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function CheckIcon(props) {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2" {...props}>
      <path d="m5 10 3.2 3.2L15 6.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function TaskIcon(props) {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" {...props}>
      <path d="M5 6.5h10M5 10h10M5 13.5h6" strokeLinecap="round" />
      <path d="M3.5 4.5h13a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1h-13a1 1 0 0 1-1-1v-9a1 1 0 0 1 1-1Z" strokeLinejoin="round" />
    </svg>
  )
}

function PeopleIcon(props) {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" {...props}>
      <path d="M6.7 9a2.2 2.2 0 1 0 0-4.4A2.2 2.2 0 0 0 6.7 9Zm6.6 0a2.2 2.2 0 1 0 0-4.4A2.2 2.2 0 0 0 13.3 9Z" />
      <path d="M3.8 15.2a3.4 3.4 0 0 1 5.8-2.4m1.1 2.4a3.4 3.4 0 0 1 5.8-2.4" strokeLinecap="round" />
    </svg>
  )
}

function DeadlineIcon(props) {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" {...props}>
      <circle cx="10" cy="10" r="7" />
      <path d="M10 6.5v4l2.7 1.7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function CommentIcon(props) {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" {...props}>
      <path d="M5 15.5 3.5 17V5a1.5 1.5 0 0 1 1.5-1.5h10A1.5 1.5 0 0 1 16.5 5v8A1.5 1.5 0 0 1 15 14.5H5Z" strokeLinejoin="round" />
      <path d="M6.5 7.5h7M6.5 10.5h5" strokeLinecap="round" />
    </svg>
  )
}

function ShieldIcon(props) {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" {...props}>
      <path d="M10 2.8 15.8 5v4.4c0 3.1-2 5.8-5.8 7.8C6.2 15.2 4.2 12.5 4.2 9.4V5L10 2.8Z" strokeLinejoin="round" />
      <path d="m7.7 10.2 1.5 1.5 3.1-3.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function InsightIcon(props) {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" {...props}>
      <path d="M4.5 14.5V10m5.5 4.5V6m5.5 8.5V8.5" strokeLinecap="round" />
      <path d="M3.5 16.5h13" strokeLinecap="round" />
    </svg>
  )
}
