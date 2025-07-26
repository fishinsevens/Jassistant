import React from 'react';

/**
 * 加载指示器尺寸配置
 */
const SPINNER_SIZES = {
  small: 'h-4 w-4',
  medium: 'h-8 w-8',
  large: 'h-12 w-12'
};

/**
 * 通用加载指示器组件
 * @param {Object} props - 组件属性
 * @param {string} props.size - 尺寸：small, medium, large
 * @param {string} props.color - 颜色，默认使用主题颜色
 * @param {string} props.className - 附加样式类
 * @param {string} props.label - 加载文本
 * @returns {JSX.Element}
 */
const Spinner = ({
  size = 'medium',
  color = 'var(--color-primary-accent)',
  className = '',
  label
}) => {
  const spinnerSize = SPINNER_SIZES[size] || SPINNER_SIZES.medium;
  
  return (
    <div className={`flex flex-col items-center ${className}`}>
      <svg
        className={`animate-spin ${spinnerSize}`}
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
      >
        <circle
          className="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          strokeWidth="4"
        ></circle>
        <path
          className="opacity-75"
          fill={color}
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
        ></path>
      </svg>
      
      {label && (
        <span className="mt-2 text-sm text-[var(--color-secondary-text)]">
          {label}
        </span>
      )}
    </div>
  );
};

/**
 * 全屏加载指示器
 * @returns {JSX.Element}
 */
export const FullPageSpinner = () => (
  <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-50 z-50">
    <Spinner size="large" label="加载中..." />
  </div>
);

export default Spinner; 