import React from 'react';

/**
 * 通用卡片组件
 * @param {Object} props - 组件属性
 * @param {ReactNode} props.children - 卡片内容
 * @param {string} props.className - 附加样式类
 * @param {string} props.title - 卡片标题
 * @param {ReactNode} props.titleExtra - 标题右侧额外内容
 * @param {boolean} props.flat - 是否扁平化显示（无阴影）
 * @param {string} props.padding - 自定义内边距
 * @returns {JSX.Element}
 */
const Card = ({ 
  children, 
  className = '', 
  title, 
  titleExtra, 
  flat = false, 
  padding = 'p-6' 
}) => {
  return (
    <div 
      className={`
        bg-[var(--color-secondary-bg)] 
        rounded-lg 
        ${!flat && 'shadow-md'} 
        ${className}
      `}
    >
      {title && (
        <div className="flex justify-between items-center px-6 py-4 border-b border-[var(--color-border)]">
          <h2 className="text-xl font-bold text-[var(--color-primary-text)]">{title}</h2>
          {titleExtra && <div>{titleExtra}</div>}
        </div>
      )}
      <div className={padding}>{children}</div>
    </div>
  );
};

export default Card; 