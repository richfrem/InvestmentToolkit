import * as React from 'react'

type MenuContextType = {
  open: boolean
  setOpen: (v: boolean) => void
}

const MenuContext = React.createContext<MenuContextType | null>(null)

export const DropdownMenu: React.FC<React.PropsWithChildren<{}>> = ({ children }) => {
  const [open, setOpen] = React.useState(false)
  const ref = React.useRef<HTMLDivElement | null>(null)

  React.useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (!ref.current) return
      if (!(e.target instanceof Node)) return
      if (!ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [])

  return (
    <div ref={ref} className="relative inline-block">
      <MenuContext.Provider value={{ open, setOpen }}>{children}</MenuContext.Provider>
    </div>
  )
}

// Trigger: expects a single child. If asChild, user will pass the element as child.
export const DropdownMenuTrigger: React.FC<React.PropsWithChildren<{}>> = ({ children }) => {
  const ctx = React.useContext(MenuContext)
  if (!ctx) return <>{children}</>

  const child = React.Children.only(children) as React.ReactElement

  const onClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    ctx.setOpen(!ctx.open)
    if (child.props.onClick) child.props.onClick(e)
  }

  return React.cloneElement(child, { onClick })
}

export const DropdownMenuContent: React.FC<React.PropsWithChildren<{ align?: 'start' | 'end' }>> = ({ children, align = 'start' }) => {
  const ctx = React.useContext(MenuContext)
  if (!ctx) return null

  if (!ctx.open) return null

  return (
    <div className={`absolute ${align === 'end' ? 'right-0' : 'left-0'} mt-2 z-50`}>
      <div className="rounded-md border bg-card p-2 shadow-md">{children}</div>
    </div>
  )
}

export const DropdownMenuCheckboxItem: React.FC<React.PropsWithChildren<{
  checked?: boolean
  onCheckedChange?: (v: boolean | 'indeterminate') => void
  className?: string
}>> = ({ children, checked = false, onCheckedChange, className = '' }) => {
  return (
    <label className={`flex items-center gap-2 px-3 py-1 cursor-pointer ${className}`}>
      <input
        type="checkbox"
        checked={!!checked}
        onChange={(e) => onCheckedChange?.(e.target.checked)}
        className="h-4 w-4"
      />
      <span className="text-sm">{children}</span>
    </label>
  )
}

export default DropdownMenu
