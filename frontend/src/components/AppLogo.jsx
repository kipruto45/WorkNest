import { Link } from 'react-router-dom'

function LogoContent({
  title,
  subtitle,
  className = '',
  imageClassName = 'h-10 w-10',
  titleClassName = '',
  subtitleClassName = '',
}) {
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <img
        src="/logo_hd.png"
        alt={`${title} logo`}
        className={`${imageClassName} rounded-xl object-cover shadow-[0_10px_24px_rgba(16,24,40,0.12)]`}
      />
      <div>
        <div className={titleClassName}>{title}</div>
        {subtitle ? <div className={subtitleClassName}>{subtitle}</div> : null}
      </div>
    </div>
  )
}

export default function AppLogo({
  to,
  title = 'WorkNest',
  subtitle = '',
  className = '',
  imageClassName,
  titleClassName,
  subtitleClassName,
}) {
  const content = (
    <LogoContent
      title={title}
      subtitle={subtitle}
      className={className}
      imageClassName={imageClassName}
      titleClassName={titleClassName}
      subtitleClassName={subtitleClassName}
    />
  )

  if (to) {
    return <Link to={to}>{content}</Link>
  }

  return content
}
