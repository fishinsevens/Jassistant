import React from 'react';
import { XMarkIcon, InformationCircleIcon, ExclamationTriangleIcon, CheckCircleIcon } from '@heroicons/react/24/outline';

/**
 * 提示类型配置
 */
const ALERT_TYPES = {
  info: {
    bg: 'bg-blue-50 dark:bg-blue-900/20',
    border: 'border-blue-400 dark:border-blue-700',
    text: 'text-blue-700 dark:text-blue-400',
    icon: InformationCircleIcon
  },
  warning: {
    bg: 'bg-yellow-50 dark:bg-yellow-900/20',
    border: 'border-yellow-400 dark:border-yellow-700',
    text: 'text-yellow-700 dark:text-yellow-400',
    icon: ExclamationTriangleIcon
  },
  error: {
    bg: 'bg-red-50 dark:bg-red-900/20',
    border: 'border-red-400 dark:border-red-700',
    text: 'text-red-700 dark:text-red-400',
    icon: ExclamationTriangleIcon
  },
  success: {
    bg: 'bg-green-50 dark:bg-green-900/20',
    border: 'border-green-400 dark:border-green-700',
    text: 'text-green-700 dark:text-green-400',
    icon: CheckCircleIcon
  }
};

/**
 * 通用Alert提示组件
 * @param {Object} props - 组件属性
 * @param {ReactNode} props.children - 提示内容
 * @param {string} props.type - 提示类型：info, warning, error, success
 * @param {string} props.title - 提示标题
 * @param {boolean} props.dismissible - 是否可关闭
 * @param {function} props.onDismiss - 关闭回调函数
 * @param {string} props.className - 附加样式类
 * @returns {JSX.Element}
 */
const Alert = ({
  children,
  type = 'info',
  title,
  dismissible = false,
  onDismiss,
  className = ''
}) => {
  const alertStyle = ALERT_TYPES[type] || ALERT_TYPES.info;
  const IconComponent = alertStyle.icon;
  
  return (
    <div
      className={`
        border-l-4
        p-4
        rounded-md
        mb-4
        flex
        ${alertStyle.bg}
        ${alertStyle.border}
        ${alertStyle.text}
        ${className}
      `}
      role="alert"
    >
      <div className="flex-shrink-0 mr-3">
        <IconComponent className="h-5 w-5" />
      </div>
      
      <div className="flex-grow">
        {title && (
          <h3 className="font-medium">{title}</h3>
        )}
        <div className={title ? 'mt-1' : ''}>
          {children}
        </div>
      </div>
      
      {dismissible && (
        <div className="flex-shrink-0">
          <button
            type="button"
            className="inline-flex rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-transparent"
            onClick={onDismiss}
          >
            <span className="sr-only">关闭</span>
            <XMarkIcon className="h-5 w-5" />
          </button>
        </div>
      )}
    </div>
  );
};

export default Alert; 