/**
 * Category dropdown select component.
 */
export default function CategorySelect({
  value,
  onChange,
  categories,
  placeholder = 'Select category...',
  allowEmpty = true,
  className = '',
}) {
  return (
    <select
      value={value || ''}
      onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}
      className={`w-full p-2 border rounded-lg bg-white ${className}`}
    >
      {allowEmpty && <option value="">{placeholder}</option>}
      {categories.map(cat => (
        <option key={cat.id} value={cat.id}>
          {cat.name}
        </option>
      ))}
    </select>
  )
}
