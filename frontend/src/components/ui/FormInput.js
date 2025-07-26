import React from 'react';

/**
 * 通用表单输入组件
 * @param {Object} props - 组件属性
 * @param {string} props.id - 输入框ID
 * @param {string} props.label - 输入框标签
 * @param {string} props.type - 输入框类型
 * @param {string} props.value - 输入框值
 * @param {function} props.onChange - 值变化处理函数
 * @param {string} props.placeholder - 占位文本
 * @param {string} props.className - 附加样式类
 * @param {boolean} props.required - 是否必填
 * @param {boolean} props.disabled - 是否禁用
 * @param {string} props.error - 错误信息
 * @param {string} props.helpText - 帮助文本
 * @param {ReactNode} props.prefix - 前缀图标或文本
 * @param {ReactNode} props.suffix - 后缀图标或文本
 * @returns {JSX.Element}
 */
const FormInput = ({
  id,
  label,
  type = 'text',
  value,
  onChange,
  placeholder,
  className = '',
  required = false,
  disabled = false,
  error,
  helpText,
  prefix,
  suffix,
  ...rest
}) => {
  // 输入框通用样式
  const inputClass = `
    input-field
    w-full
    bg-[var(--color-sidebar-bg)]
    text-[var(--color-primary-text)]
    border
    rounded-md
    focus:ring-2
    focus:ring-[var(--color-primary-accent)]
    focus:border-[var(--color-primary-accent)]
    placeholder-[var(--color-secondary-text)]
    ${error ? 'border-[var(--color-danger)]' : 'border-[var(--color-border)]'}
    ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
    ${prefix ? 'pl-10' : ''}
    ${suffix ? 'pr-10' : ''}
    ${className}
  `;

  return (
    <div className="mb-4">
      {label && (
        <label
          htmlFor={id}
          className={`block text-[var(--color-primary-text)] font-medium mb-1 ${required ? 'required' : ''}`}
        >
          {label}
          {required && <span className="text-[var(--color-danger)] ml-1">*</span>}
        </label>
      )}
      
      <div className="relative">
        {prefix && (
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            {prefix}
          </div>
        )}
        
        {type === 'textarea' ? (
          <textarea
            id={id}
            value={value}
            onChange={onChange}
            placeholder={placeholder}
            disabled={disabled}
            className={inputClass}
            rows={5}
            {...rest}
          />
        ) : (
          <input
            id={id}
            type={type}
            value={value}
            onChange={onChange}
            placeholder={placeholder}
            disabled={disabled}
            className={inputClass}
            {...rest}
          />
        )}
        
        {suffix && (
          <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
            {suffix}
          </div>
        )}
      </div>
      
      {error && (
        <p className="mt-1 text-sm text-[var(--color-danger)]">{error}</p>
      )}
      
      {helpText && !error && (
        <p className="mt-1 text-sm text-[var(--color-secondary-text)]">{helpText}</p>
      )}
    </div>
  );
};

export default FormInput; 