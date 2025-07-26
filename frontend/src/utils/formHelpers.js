/**
 * 表单验证规则类型
 */
export const VALIDATOR_TYPES = {
  REQUIRED: 'REQUIRED',
  MIN_LENGTH: 'MIN_LENGTH',
  MAX_LENGTH: 'MAX_LENGTH',
  EMAIL: 'EMAIL',
  NUMERIC: 'NUMERIC',
  REGEX: 'REGEX',
  CUSTOM: 'CUSTOM',
};

/**
 * 创建必填验证器
 * @param {string} errorMessage - 错误信息
 * @returns {Object} 验证器对象
 */
export const required = (errorMessage = '此字段为必填项') => ({
  type: VALIDATOR_TYPES.REQUIRED,
  errorMessage
});

/**
 * 创建最小长度验证器
 * @param {number} length - 最小长度
 * @param {string} errorMessage - 错误信息
 * @returns {Object} 验证器对象
 */
export const minLength = (length, errorMessage = `最少需要 ${length} 个字符`) => ({
  type: VALIDATOR_TYPES.MIN_LENGTH,
  length,
  errorMessage
});

/**
 * 创建最大长度验证器
 * @param {number} length - 最大长度
 * @param {string} errorMessage - 错误信息
 * @returns {Object} 验证器对象
 */
export const maxLength = (length, errorMessage = `最多允许 ${length} 个字符`) => ({
  type: VALIDATOR_TYPES.MAX_LENGTH,
  length,
  errorMessage
});

/**
 * 创建邮箱验证器
 * @param {string} errorMessage - 错误信息
 * @returns {Object} 验证器对象
 */
export const email = (errorMessage = '请输入有效的电子邮箱地址') => ({
  type: VALIDATOR_TYPES.EMAIL,
  errorMessage
});

/**
 * 创建数字验证器
 * @param {string} errorMessage - 错误信息
 * @returns {Object} 验证器对象
 */
export const numeric = (errorMessage = '请输入有效的数字') => ({
  type: VALIDATOR_TYPES.NUMERIC,
  errorMessage
});

/**
 * 创建正则表达式验证器
 * @param {RegExp} pattern - 正则表达式
 * @param {string} errorMessage - 错误信息
 * @returns {Object} 验证器对象
 */
export const regex = (pattern, errorMessage = '输入格式不正确') => ({
  type: VALIDATOR_TYPES.REGEX,
  pattern,
  errorMessage
});

/**
 * 创建自定义验证器
 * @param {function} validator - 验证函数，接收值参数，返回布尔值
 * @param {string} errorMessage - 错误信息
 * @returns {Object} 验证器对象
 */
export const custom = (validator, errorMessage = '输入无效') => ({
  type: VALIDATOR_TYPES.CUSTOM,
  validator,
  errorMessage
});

/**
 * 验证单个表单字段
 * @param {any} value - 字段值
 * @param {Array} validators - 验证器数组
 * @returns {Object} 验证结果，包含isValid和errorMessage
 */
export const validateField = (value, validators = []) => {
  if (!validators || validators.length === 0) {
    return { isValid: true, errorMessage: '' };
  }

  for (const validator of validators) {
    switch (validator.type) {
      case VALIDATOR_TYPES.REQUIRED:
        if (!value || (typeof value === 'string' && value.trim() === '')) {
          return { isValid: false, errorMessage: validator.errorMessage };
        }
        break;
      case VALIDATOR_TYPES.MIN_LENGTH:
        if (!value || value.length < validator.length) {
          return { isValid: false, errorMessage: validator.errorMessage };
        }
        break;
      case VALIDATOR_TYPES.MAX_LENGTH:
        if (value && value.length > validator.length) {
          return { isValid: false, errorMessage: validator.errorMessage };
        }
        break;
      case VALIDATOR_TYPES.EMAIL:
        // 简单的邮箱验证正则
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(value)) {
          return { isValid: false, errorMessage: validator.errorMessage };
        }
        break;
      case VALIDATOR_TYPES.NUMERIC:
        if (isNaN(Number(value))) {
          return { isValid: false, errorMessage: validator.errorMessage };
        }
        break;
      case VALIDATOR_TYPES.REGEX:
        if (!validator.pattern.test(value)) {
          return { isValid: false, errorMessage: validator.errorMessage };
        }
        break;
      case VALIDATOR_TYPES.CUSTOM:
        if (!validator.validator(value)) {
          return { isValid: false, errorMessage: validator.errorMessage };
        }
        break;
      default:
        break;
    }
  }

  return { isValid: true, errorMessage: '' };
};

/**
 * 验证整个表单
 * @param {Object} formValues - 表单值对象
 * @param {Object} validationSchema - 验证规则对象，键为字段名，值为验证器数组
 * @returns {Object} 验证结果，包含isValid布尔值和errors对象
 */
export const validateForm = (formValues, validationSchema) => {
  const errors = {};
  let isValid = true;

  Object.keys(validationSchema).forEach(fieldName => {
    const fieldValidators = validationSchema[fieldName];
    const fieldValue = formValues[fieldName];

    const result = validateField(fieldValue, fieldValidators);
    
    if (!result.isValid) {
      errors[fieldName] = result.errorMessage;
      isValid = false;
    }
  });

  return { isValid, errors };
}; 