import React from 'react';

/**
 * 按钮类型对应的样式
 */
const BUTTON_TYPES = {
  primary: 'bg-[var(--color-primary-accent)] text-white hover:bg-opacity-80',
  secondary: 'bg-[var(--color-sidebar-bg)] text-[var(--color-primary-text)] hover:bg-opacity-80',
  danger: 'bg-[var(--color-danger)] text-white hover:bg-opacity-80',
  success: 'bg-[var(--color-secondary-accent)] text-white hover:bg-opacity-80',
  link: 'bg-transparent text-[var(--color-primary-accent)] hover:underline p-0',
};

/**
 * 按钮大小对应的样式
 */
const BUTTON_SIZES = {
  small: 'py-1 px-3 text-sm',
  medium: 'py-2 px-4',
  large: 'py-3 px-6 text-lg',
};

/**
 * 通用按钮组件
 * @param {Object} props - 组件属性
 * @param {ReactNode} props.children - 按钮内容
 * @param {string} props.type - 按钮类型：primary, secondary, danger, success, link
 * @param {string} props.size - 按钮大小：small, medium, large
 * @param {boolean} props.disabled - 是否禁用
 * @param {boolean} props.isLoading - 是否加载中
 * @param {function} props.onClick - 点击事件处理函数
 * @param {string} props.className - 附加样式类
 * @param {ReactNode} props.icon - 图标组件
 * @param {boolean} props.iconOnly - 是否只显示图标
 * @param {boolean} props.fullWidth - 是否宽度100%
 * @returns {JSX.Element}
 */
const Button = ({
  children,
  type = 'primary',
  size = 'medium',
  disabled = false,
  isLoading = false,
  onClick,
  className = '',
  icon,
  iconOnly = false,
  fullWidth = false,
  ...rest
}) => {
  const buttonClass = `
    ${BUTTON_TYPES[type] || BUTTON_TYPES.primary}
    ${BUTTON_SIZES[size] || BUTTON_SIZES.medium}
    ${fullWidth ? 'w-full' : ''}
    ${isLoading || disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
    transition-colors duration-200
    flex items-center justify-center gap-2
    font-medium rounded-md
    ${iconOnly ? 'p-2' : ''}
    ${className}
  `;

  return (
    <button
      onClick={!disabled && !isLoading ? onClick : undefined}
      disabled={disabled || isLoading}
      className={buttonClass}
      {...rest}
    >
      {isLoading && (
        <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
      )}
      {icon && <span className={iconOnly ? 'sr-only' : ''}>{icon}</span>}
      {(!iconOnly || !icon) && children}
    </button>
  );
};

export default Button; 